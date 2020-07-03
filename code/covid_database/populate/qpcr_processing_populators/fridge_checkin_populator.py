import logging
from abc import ABC
from typing import List

import pandas as pd
from sqlalchemy.orm.exc import NoResultFound

import covidhub.constants.qpcr_forms as forms
from covid_database.models.qpcr_processing import (
    Fridge,
    FridgeCheckin,
    Researcher,
    SamplePlate,
)
from covid_database.populate.base import (
    BaseWorksheetPopulator,
    RemoteWorksheetPopulatorMixin,
)

log = logging.getLogger(__name__)


class FridgeCheckinPopulator(BaseWorksheetPopulator, ABC):
    """
    Class that populates all data about fridge checkins.
    """

    @property
    def models_to_populate(self) -> List[str]:
        return [
            FridgeCheckin.__name__,
        ]

    def populate_models(self):
        """
        Iterate through rows in 4c check in form
        """
        log.info("populating fridge check-ins...")
        existing_samples_times = {
            (m.sample_plate, m.created_at)
            for m in self.session.query(FridgeCheckin).all()
        }

        for index, row in self.data.iterrows():
            # for empty rows
            if all(pd.isna(row)):
                continue

            timestamp = row[forms.FridgeCheckin.TIMESTAMP]
            researcher_name = row[forms.FridgeCheckin.RESEARCHER_NAME]
            sample_barcode = row[forms.FridgeCheckin.SAMPLE_PLATE_BARCODE]
            fridge_name = row[forms.FridgeCheckin.FRIDGE]

            # if just the barcode is missing, log it
            if pd.isna(sample_barcode):
                log.critical(
                    "No sample plate barcode, skipping", extra={"notify_slack": True}
                )
                continue
            elif (sample_barcode, timestamp) in existing_samples_times:
                continue

            try:
                fridge = (
                    self.session.query(Fridge).filter(Fridge.name == fridge_name).one()
                )
            except NoResultFound:
                log.critical(
                    f"Can't find fridge {fridge_name}, skipping",
                    extra={"notify_slack": True},
                )
                continue

            shelf = int(row[forms.FridgeCheckin.SHELF])
            rack = int(row[forms.FridgeCheckin.RACK])
            plate = int(row[forms.FridgeCheckin.PLATE].replace("Plate ", ""))
            notes = row[forms.FridgeCheckin.NOTES]

            try:
                researcher = (
                    self.session.query(Researcher)
                    .filter(Researcher.name == researcher_name)
                    .one()
                )
            except NoResultFound:
                log.debug(f"Can't find researcher {researcher_name}, skipping")
                continue

            try:
                sample_plate = (
                    self.session.query(SamplePlate)
                    .filter(SamplePlate.barcode == sample_barcode)
                    .one()
                )
            except NoResultFound:
                log.debug(f"Can't find sample plate {sample_barcode}, skipping")
                continue

            log.debug(f"{sample_barcode} checked in to {fridge_name} at {timestamp}")
            fridge_checkin = FridgeCheckin(
                created_at=timestamp,
                researcher=researcher,
                sample_plate=sample_plate,
                fridge=fridge,
                shelf=shelf,
                rack=rack,
                plate=plate,
                notes=notes,
            )
            self.session.add(fridge_checkin)


class RemoteFridgeCheckinPopulator(
    RemoteWorksheetPopulatorMixin, FridgeCheckinPopulator
):
    """
    Class that populates all relevant data from the google worksheet '4C check in'
    """

    @property
    def spreadsheet_id_config_key(self) -> str:
        return "collection_form_spreadsheet_id"

    @property
    def sheet_name(self) -> str:
        return forms.FridgeCheckin.SHEET_NAME

    @property
    def skip_header(self) -> bool:
        return True
