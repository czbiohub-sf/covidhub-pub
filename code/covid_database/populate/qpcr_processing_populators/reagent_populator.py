import logging
from abc import ABC
from typing import List

import pandas as pd
from pkg_resources import resource_filename
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound

from covid_database.models.enums import Protocol, ReagentPlateType
from covid_database.models.qpcr_processing import (
    Plate,
    PlatePrep,
    QPCRPlate,
    Reagent,
    ReagentLot,
    ReagentPlate,
    Researcher,
    RNAPlate,
    SamplePlate,
)
from covid_database.populate.base import (
    BaseLocalYamlPopulator,
    BaseWorksheetPopulator,
    RemoteWorksheetPopulatorMixin,
)
from covidhub.constants.qpcr_forms.reagent_prep import QPCR, ReagentPrep, RNA, SP

log = logging.getLogger(__name__)


class ReagentPopulator(BaseLocalYamlPopulator):
    """
    Class that populates reagent table form protocols.yaml in qpcr_processing

    Parameters
    ----------
    :param session: An open DB session object
    :param config: Config instance
    :param drive_service: An authenticated gdrive service object
    """

    PATH_TO_REAGENT_YAML = resource_filename("covid_database", "reagents.yaml")

    def __init__(self, session: Session, **kwargs):
        super().__init__(
            session=session,
            path_to_file=ReagentPopulator.PATH_TO_REAGENT_YAML,
            **kwargs,
        )

    @property
    def models_to_populate(self) -> List[str]:
        """The models that the ProtocolPopulator will create and inset into the DB"""
        return [Reagent.__name__]

    def populate_models(self):
        """Create all models and insert into DB"""
        log.info("populating reagents")
        existing_reagents = {
            reagent.name for reagent in self.session.query(Reagent).all()
        }
        self.session.add_all(
            Reagent(name=reagent_name)
            for reagent_name in self.data
            if reagent_name not in existing_reagents
        )


class ReagentPrepPopulator(BaseWorksheetPopulator, ABC):
    """
    Class that populates all reagent prep data.
    """

    @property
    def models_to_populate(self) -> List[str]:
        return [
            PlatePrep.__name__,
            QPCRPlate.__name__,
            ReagentLot.__name__,
            ReagentPlate.__name__,
            SamplePlate.__name__,
        ]

    def populate_models(self):
        """
        Iterate through rows in Reagent Form
        """
        log.info("populating reagent plates, lots, and preps...")

        # assuming here that a single researcher cannot submit two preps simultaneously
        existing_preps = {
            (prep.researcher.name, prep.created_at)
            for prep in self.session.query(PlatePrep)
        }

        for index, row in self.data.iterrows():
            timestamp = row[ReagentPrep.TIMESTAMP]
            plate_type = row[ReagentPrep.PLATE_TYPE]
            researcher_name = row[ReagentPrep.RESEARCHER_NAME]

            if (researcher_name, timestamp) in existing_preps:
                log.debug("Already registered these plates, skipping")
                continue

            if pd.isna(plate_type):
                log.error("No plate type specified, skipping")
                continue
            elif pd.isna(researcher_name):
                log.error("No researcher specified, skipping")
                continue

            try:
                researcher = (
                    self.session.query(Researcher)
                    .filter(Researcher.name == researcher_name)
                    .one()
                )
            except NoResultFound:
                log.debug(f"Can't find researcher {researcher_name}, skipping")
                continue

            plate_cls = ReagentPrep.PLATE_TYPES[plate_type]
            lot_set = set()
            notes = None

            log.debug(f"Adding reagent lots for {plate_type}")
            if plate_cls == QPCR:
                qpcr_type = row[ReagentPrep.QPCR_TYPE]
                if pd.isna(qpcr_type):
                    log.critical(
                        "Missing qPCR type for qPCR plate, skipping",
                        extra={"notify_slack": True},
                    )
                    continue
                elif qpcr_type not in plate_cls:
                    log.critical(
                        f"Unknown qPCR type {qpcr_type}", extra={"notify_slack": True}
                    )
                    continue

                qpcr_cls = plate_cls[qpcr_type]

                for col in qpcr_cls.columns():
                    col_name = col.split("_", 2)[2]
                    if col_name == "notes":
                        notes = row[col]
                    else:
                        log.debug(f"Adding reagent lot: {col_name}")
                        lot_set.update(
                            (col_name, lot.strip()) for lot in str(row[col]).split(",")
                        )

                model_cls = QPCRPlate
                kwargs = {"protocol": Protocol(qpcr_cls.NAME)}
            else:
                if plate_cls == SP:
                    model_cls = SamplePlate
                    kwargs = {}
                elif plate_cls == RNA:
                    model_cls = RNAPlate
                    kwargs = {}
                else:
                    model_cls = ReagentPlate
                    kwargs = {
                        "reagent_plate_type": ReagentPlateType(plate_cls.__name__)
                    }

                for col in plate_cls.columns():
                    reagent_name = col.split("_", 1)[1]
                    log.debug(f"Adding reagent lot: {reagent_name}")
                    if pd.notna(row[col]):
                        lot_set.update(
                            (reagent_name, lot.strip())
                            for lot in str(row[col]).split(",")
                        )
                    else:
                        log.critical(
                            f"Missing {reagent_name} reagent lot made at {timestamp}",
                            extra={"notify_slack": True},
                        )

            reagent_lots = [
                self.get_reagent_lot(self.get_reagent(reagent_name), lot)
                for reagent_name, lot in lot_set
            ]

            self.session.add_all(reagent_lots)

            prep = PlatePrep(
                created_at=timestamp,
                researcher=researcher,
                notes=notes,
                reagent_lots=reagent_lots,
            )
            log.debug(f"Adding prep by {prep.researcher.name}")
            log.debug(
                f"Lots: {', '.join(lot.reagent_lot for lot in prep.reagent_lots)}"
            )

            plate_barcodes = {
                plate.barcode for plate in self.session.query(Plate).all()
            }
            plates = []

            for column in ReagentPrep.REAGENT_PLATE_BARCODES:
                barcode = row[column]
                if pd.isnull(barcode):
                    continue

                if barcode in plate_barcodes:
                    log.debug(f"barcode {barcode} exists already, skipping")
                    continue

                log.debug(f"Adding {plate_type} plate: {barcode}")
                plate_barcodes.add(barcode)
                plates.append(model_cls(barcode=barcode, prep=prep, **kwargs))

            if plates:
                self.session.add(prep)
                self.session.add_all(plates)
            self.session.flush()

    def get_reagent(self, reagent_name):
        try:
            reagent = (
                self.session.query(Reagent).filter(Reagent.name == reagent_name).one()
            )
        except NoResultFound:
            logging.exception(f"No reagent found for {reagent_name}")
            raise

        return reagent

    def get_reagent_lot(self, reagent, lot_num):
        """Create ReagentLot objects given a string of possibly multiple lot numbers"""

        reagent_lot = (
            self.session.query(ReagentLot)
            .filter(ReagentLot.reagent == reagent)
            .filter(ReagentLot.reagent_lot == lot_num)
            .one_or_none()
        )
        if reagent_lot is None:
            log.debug(f"Adding reagent lot for {reagent.name}: {lot_num}")
            reagent_lot = ReagentLot(reagent=reagent, reagent_lot=lot_num)

        return reagent_lot


class RemoteReagentPrepPopulator(RemoteWorksheetPopulatorMixin, ReagentPrepPopulator):
    """
    Class that populates all relevant data from the google worksheet Reagent Tracking
    """

    @property
    def spreadsheet_id_config_key(self) -> str:
        return "collection_form_spreadsheet_id"

    @property
    def sheet_name(self) -> str:
        return ReagentPrep.SHEET_NAME

    @property
    def skip_header(self) -> bool:
        return True
