import logging
from abc import ABC
from typing import List

import pandas as pd
from sqlalchemy.orm.exc import NoResultFound

import covidhub.constants.qpcr_forms as forms
from covid_database.models.qpcr_processing import (
    Aliquoting,
    BravoStation,
    Extraction,
    QPCRPlate,
    ReagentPlate,
    Researcher,
    RNAPlate,
    SamplePlate,
)
from covid_database.populate.base import (
    BaseWorksheetPopulator,
    RemoteWorksheetPopulatorMixin,
)

log = logging.getLogger(__name__)


class RNAExtractionPopulator(BaseWorksheetPopulator, ABC):
    """
    Class that populates all Bravo RNA extractions.

    Note: RNA aliquoting is also inferred from the dataframe.
    """

    @property
    def models_to_populate(self) -> List[str]:
        return [Extraction.__name__, Aliquoting.__name__]

    def populate_models(self):
        """
        Iterate through rows in Bravo RNA extractions form data and insert Extraction
        and Aliquoting entries for each registered plate
        """
        log.info("populating Extractions and Aliquoting")

        existing_extraction = {
            m.rna_plate.barcode for m in self.session.query(Extraction).all()
        }

        for index, row in self.data.iterrows():
            rna_barcode = row[forms.BravoRNAExtraction.RNA_PLATE_BARCODE]

            if rna_barcode in existing_extraction:
                log.debug(f"Skipping extraction for existing barcode {rna_barcode}")
                continue

            timestamp = row[forms.BravoRNAExtraction.TIMESTAMP]
            researcher_name = row[forms.BravoRNAExtraction.RESEARCHER_NAME]
            notes = row[forms.BravoRNAExtraction.NOTES]

            try:
                researcher = (
                    self.session.query(Researcher)
                    .filter(Researcher.name == researcher_name)
                    .one()
                )
            except NoResultFound:
                log.exception(f"Unknown researcher {researcher_name}")
                raise

            # UCSF person responsible for this extraction
            cliahub_researcher_name = row[forms.BravoRNAExtraction.CLIAHUB_RESEARCHER]

            try:
                cliahub_researcher = (
                    self.session.query(Researcher)
                    .filter(Researcher.name == cliahub_researcher_name)
                    .filter(Researcher.clia_certified)
                    .one()
                )
            except NoResultFound:
                log.exception(f"Unknown CLIAHub Researcher {cliahub_researcher_name}")
                continue

            sample_plate_barcode = row[forms.BravoRNAExtraction.SAMPLE_PLATE_BARCODE]

            try:
                sample_plate = (
                    self.session.query(SamplePlate)
                    .filter(SamplePlate.barcode == sample_plate_barcode)
                    .one()
                )
            except NoResultFound:
                log.critical(
                    f"Unknown sample plate {sample_plate_barcode}, skipping",
                    extra={"notify_slack": True},
                )
                continue

            reagent_plate_barcodes = [
                row[COL]
                for COL in forms.BravoRNAExtraction.REAGENT_PLATES
                if not pd.isna(row[COL])
            ]

            # The Extraction model will validate that these all exist
            reagent_plates = (
                self.session.query(ReagentPlate)
                .filter(ReagentPlate.barcode.in_(reagent_plate_barcodes))
                .all()
            )

            # this is usually the first place that RNA plate barcodes are seen because
            # they contain no reagents, but they _can_ be registered by the reagent team
            # if they were sealed
            if pd.isna(row[forms.BravoRNAExtraction.RNA_PLATE_BARCODE]):
                log.critical(
                    f"No RNA plate barcode for sample_plate {sample_plate_barcode}",
                    extra={"notify_slack": True},
                )
                continue

            rna_plate = self.get_rna_plate(rna_barcode)
            bravo_station = self.get_bravo(row[forms.BravoRNAExtraction.BRAVO_STATION])
            qpcr_plate = self.get_qpcr_plate(
                row[forms.BravoRNAExtraction.QPCR_PLATE_BARCODE]
            )

            extraction = Extraction(
                created_at=timestamp,
                bravo=bravo_station,
                researcher=researcher,
                cliahub_researcher=cliahub_researcher,
                sample_plate=sample_plate,
                rna_plate=rna_plate,
                reagent_plates=reagent_plates,
                notes=notes,
            )
            log.debug(f"Adding Extraction {extraction}")
            self.session.add(extraction)

            aliquoting = Aliquoting(
                created_at=timestamp,
                bravo=bravo_station,
                researcher=researcher,
                rna_plate=rna_plate,
                qpcr_plate=qpcr_plate,
                notes=notes,
            )

            log.debug(f"Adding Aliquoting {aliquoting}")
            self.session.add(aliquoting)

        self.session.flush()

    def get_bravo(self, bravo_station_name: str) -> BravoStation:
        """Get a BravoStation. These should always exist"""

        try:
            bravo_station = (
                self.session.query(BravoStation)
                .filter(BravoStation.name == bravo_station_name)
                .one()
            )
        except NoResultFound:
            log.critical(
                f"No Bravo station found for {bravo_station_name}",
                extra={"notify_slack": True},
            )
            raise

        return bravo_station

    def get_rna_plate(self, rna_barcode: str) -> RNAPlate:
        """Create an RNAPlate instance, or return it if it already exists."""

        rna_plate = (
            self.session.query(RNAPlate)
            .filter(RNAPlate.barcode == rna_barcode)
            .one_or_none()
        )
        if rna_plate is None:
            log.debug(f"Adding RNA plate: {rna_barcode}")
            rna_plate = RNAPlate(barcode=rna_barcode)
            self.session.add(rna_plate)

        return rna_plate

    def get_qpcr_plate(self, qpcr_barcode: str) -> QPCRPlate:
        """Find the qPCR plate that was aliquoted into. This should always exist because
        it was prepped by the reagent team.
        """

        try:
            qpcr_plate = (
                self.session.query(QPCRPlate)
                .filter(QPCRPlate.barcode == qpcr_barcode)
                .one()
            )
        except NoResultFound:
            log.exception(f"No qpcr plate found with barcode {qpcr_barcode}")
            raise

        return qpcr_plate


class RemoteRNAExtractionPopulator(
    RemoteWorksheetPopulatorMixin, RNAExtractionPopulator
):
    """
    Class that populates all relevant data from the google worksheet Bravo RNA
    extractions.

    Note: RNA aliquoting is also inferred from this worksheet
    """

    @property
    def spreadsheet_id_config_key(self) -> str:
        return "collection_form_spreadsheet_id"

    @property
    def sheet_name(self) -> str:
        return forms.BravoRNAExtraction.SHEET_NAME

    @property
    def skip_header(self) -> bool:
        return True
