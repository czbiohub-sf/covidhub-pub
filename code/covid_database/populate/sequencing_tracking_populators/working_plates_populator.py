import logging
from abc import ABC
from typing import List

import pandas as pd
from sqlalchemy.orm import Session

from covid_database.models.ngs_sample_tracking import (
    CZBID,
    CZBIDOgPlate,
    CZBIDThaw,
    CZBIDWorkingPlate,
    WorkingPlate,
)
from covid_database.populate.base import (
    BaseDriveFolderPopulator,
    BaseWorksheetPopulator,
    RemoteWorksheetPopulatorMixin,
)
from covid_database.populate.sequencing_tracking_populators.utils import check_control
from covidhub.config import Config
from covidhub.google.drive import DriveService, find_file_by_search_terms, FindMode

log = logging.getLogger(__name__)

HEADER_1 = {"barcode": "96 COMET Plate Barcode", "file_url": "96 COMET Sample ID file"}

HEADER_2 = {
    "barcode": "96 COMET Destination Plate Barcode",
    "file_url": "96 COMET Source Plate File (OG or RX)",
}


class WorkingPlatesPopulator(BaseWorksheetPopulator, ABC):
    """
    Class that populates all COMET working plates.
    """

    @property
    def models_to_populate(self) -> List[str]:
        """The models that the FormChoicesPopulator will create and inset into the DB"""
        return [WorkingPlate.__name__, CZBIDWorkingPlate.__name__, CZBIDThaw.__name__]

    def populate_models(self):
        """Create all models and insert into DB"""
        existing_working_plate_models = self.session.query(WorkingPlate).all()
        existing_working_plate_barcodes = {
            result.barcode for result in existing_working_plate_models
        }

        log.info("populating working plate metadata")
        barcdoes_set_1 = set(self.data[HEADER_1["barcode"]].dropna())
        for working_plate in barcdoes_set_1:
            if working_plate not in existing_working_plate_barcodes:
                self.add_working_plate(working_plate, HEADER_1)
                existing_working_plate_barcodes.add(working_plate)
        barcodes_set_2 = set(self.data[HEADER_2["barcode"]].dropna())
        for working_plate in barcodes_set_2:
            if working_plate not in existing_working_plate_barcodes:
                self.add_working_plate(working_plate, HEADER_2)
                existing_working_plate_barcodes.add(working_plate)

    def add_working_plate(self, working_plate, header):
        notes = list(
            self.data.loc[self.data[header["barcode"]] == working_plate][
                "Notes"
            ].dropna()
        )
        created_date = list(
            self.data.loc[self.data[header["barcode"]] == working_plate][
                "Timestamp"
            ].dropna()
        )
        notes = notes[0] if len(notes) != 0 else None
        created_date = created_date[0] if len(created_date) != 0 else None
        # create working plate
        working_plate_model = WorkingPlate(
            barcode=working_plate, created_date=created_date, notes=notes
        )
        self.session.add(working_plate_model)
        self.session.flush()


class RemoteWorkingPlatesPopulator(
    RemoteWorksheetPopulatorMixin, WorkingPlatesPopulator
):
    """
    Class that populates all relevant data from the google worksheet COMET Input Plate
    """

    @property
    def spreadsheet_id_config_key(self) -> str:
        return "mNGS_sample_tracking_form_responses_sheet_id"

    @property
    def sheet_name(self) -> str:
        return "COMET Input Plate"


class CZBIDToWorkingPlatePopulator(BaseDriveFolderPopulator):
    """
    Class that populates all relevant data from the working plate layout drive folder

    Parameters
    ----------
    :param session: An open DB session object
    :param config: Config instance
    :param drive_service: An authenticated gdrive service object
    """

    def __init__(self, session: Session, drive_service: DriveService, cfg: Config):
        working_plate_layout = (
            cfg.INPUT_GDRIVE_PATH + cfg["DATA"]["working_plate_layout_folder"]
        )
        super().__init__(
            session=session,
            drive_service=drive_service,
            folder_path_components=working_plate_layout,
        )

    @property
    def models_to_populate(self) -> List[str]:
        """The models that the FormChoicesPopulator will create and inset into the DB"""
        return [CZBIDWorkingPlate.__name__, CZBIDThaw.__name__]

    def populate_models(self):
        """Create all models and insert into DB"""
        # get all working plates, lookup coresponding plate layout file and get czb ids from that
        working_plate_models = self.session.query(WorkingPlate).all()
        og_plates_taken_out = set()

        existing_czb_id_to_working_plate_models = self.session.query(
            CZBIDWorkingPlate
        ).all()
        existing_czb_id_to_working_plates = {
            f"{result.czb_id}-{result.working_plate_id}"
            for result in existing_czb_id_to_working_plate_models
        }
        for working_plate in working_plate_models:
            plate_layout_file = find_file_by_search_terms(
                service=self.drive_service,
                folder_id=self.folder_id,
                search_terms=[working_plate.barcode, ".csv"],
                find_mode=FindMode.MOST_RECENTLY_MODIFIED,
            )
            with plate_layout_file.open() as fh:
                if plate_layout_file.name.endswith(".xlsx"):
                    plate_layout_data = pd.read_excel(fh)
                else:
                    plate_layout_data = pd.read_csv(fh)
                czb_ids_to_well = (
                    plate_layout_data[["CZB_ID", "Destination_Well"]].dropna().values
                )
                for czb_id, well in czb_ids_to_well:
                    if (
                        f"{czb_id}-{working_plate.id}"
                        in existing_czb_id_to_working_plates
                    ) or check_control(czb_id):
                        continue
                    czb_id_model = (
                        self.session.query(CZBID)
                        .filter(CZBID.czb_id == czb_id)
                        .one_or_none()
                    )
                    if not czb_id_model:
                        log.error(f"Did not find entry for {czb_id}")
                        continue
                    # check for og plate association for thaws
                    czb_id_to_og_plate_model = (
                        self.session.query(CZBIDOgPlate)
                        .filter(CZBIDOgPlate.czb_id_id == czb_id_model.id)
                        .one_or_none()
                    )
                    if not czb_id_to_og_plate_model:
                        # must be internal sample. Add first thaw
                        self.session.add(
                            CZBIDThaw(czb_id_id=czb_id_model.id, volume_removed=20)
                        )
                    else:
                        og_plates_taken_out.add(czb_id_to_og_plate_model.og_plate)
                    self.session.add(
                        CZBIDWorkingPlate(
                            czb_id=czb_id_model,
                            working_plate_id=working_plate.id,
                            well_id=well,
                        )
                    )
        for og_plate in og_plates_taken_out:
            all_czb_ids_on_og_plate = (
                self.session.query(CZBIDOgPlate)
                .filter(CZBIDOgPlate.og_plate == og_plate)
                .all()
            )
            for model in all_czb_ids_on_og_plate:
                self.session.add(
                    CZBIDThaw(czb_id_id=model.czb_id_id, volume_removed=20)
                )
