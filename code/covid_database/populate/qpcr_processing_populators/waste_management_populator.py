import logging
from abc import ABC
from typing import List

import pandas as pd
from sqlalchemy.orm.exc import NoResultFound

from covid_database.models.qpcr_processing import (
    BottleWasteManagement,
    DrumWasteManagement,
    Plate,
    PlateWasteManagement,
    Researcher,
)
from covid_database.populate.base import (
    BaseWorksheetPopulator,
    RemoteWorksheetPopulatorMixin,
)
from covidhub.constants import qpcr_forms as forms

log = logging.getLogger(__name__)


class WasteManagementPopulator(BaseWorksheetPopulator, ABC):
    """
    Class that populates all waste management data.
    """

    @property
    def models_to_populate(self) -> List[str]:
        return [
            BottleWasteManagement.__name__,
            DrumWasteManagement.__name__,
            PlateWasteManagement.__name__,
        ]

    def populate_models(self):
        """
        Iterate through rows in waste discard check in form
        """

        existing_plate_barcodes = {
            p.plate_id for p in self.session.query(PlateWasteManagement).all()
        }

        existing_bottle_ids = {
            p.bottle_id for p in self.session.query(BottleWasteManagement).all()
        }

        existing_drum_ids = {
            p.drum_id for p in self.session.query(DrumWasteManagement).all()
        }

        log.info("populating waste discard check-ins...")
        for index, row in self.data.iterrows():
            if all(pd.isna(row)):
                continue

            timestamp = row[forms.WasteManagement.TIMESTAMP]
            researcher_name = row[forms.WasteManagement.RESEARCHER_NAME]

            for column in forms.WasteManagement.columns():
                if column == "notes":
                    # There is no notes column in the spreadsheet.  Instead, there is a
                    # column for notes corresponding to each class of waste.
                    continue
                value = row[column]
                if pd.isna(value):
                    continue

                try:
                    researcher = (
                        self.session.query(Researcher)
                        .filter(Researcher.name == researcher_name)
                        .one()
                    )
                except NoResultFound:
                    log.critical(
                        f"Can't find researcher {researcher_name}, skipping",
                        extra={"notify_slack": True},
                    )
                    continue

                if (
                    column in forms.WasteManagement.DRUMS
                    and value not in existing_drum_ids
                ):
                    # create an entry for drum
                    log.debug(f"Drum waste {value}")
                    waste = DrumWasteManagement(
                        created_at=timestamp,
                        researcher=researcher,
                        drum_id=value,
                        notes=row[forms.WasteManagement.DRUMS_NOTES],
                    )
                elif (
                    column in forms.WasteManagement.BOTTLES
                    and value not in existing_bottle_ids
                ):
                    # create an entry for bottle
                    log.debug(f"Bottle waste {value}")
                    waste = BottleWasteManagement(
                        created_at=timestamp,
                        researcher=researcher,
                        bottle_id=value,
                        notes=row[forms.WasteManagement.BOTTLES_NOTES],
                    )
                elif (
                    column in forms.WasteManagement.PLATES
                    and value not in existing_plate_barcodes
                ):
                    try:
                        plate = (
                            self.session.query(Plate)
                            .filter(Plate.barcode == value)
                            .one()
                        )
                    except NoResultFound:
                        log.critical(
                            f"Can't find plate {value}, skipping",
                            extra={"notify_slack": True},
                        )
                        continue

                    # create an entry for plate
                    log.debug(f"Plate waste {plate}")
                    waste = PlateWasteManagement(
                        created_at=timestamp,
                        researcher=researcher,
                        plate=plate,
                        notes=row[forms.WasteManagement.PLATES_NOTES],
                    )
                else:
                    continue

                self.session.add(waste)


class RemoteWasteManagementPopulator(
    RemoteWorksheetPopulatorMixin, WasteManagementPopulator
):
    """
    Class that populates all relevant data from the google worksheet 'Waste Discard'
    """

    @property
    def spreadsheet_id_config_key(self) -> str:
        return "collection_form_spreadsheet_id"

    @property
    def sheet_name(self) -> str:
        return forms.WasteManagement.SHEET_NAME

    @property
    def skip_header(self) -> bool:
        return True
