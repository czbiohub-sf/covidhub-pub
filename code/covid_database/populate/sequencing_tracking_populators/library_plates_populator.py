import logging
from typing import List

import pandas as pd
from sqlalchemy.orm import Session

from covid_database.models.ngs_sample_tracking import (
    CZBID,
    CZBIDLibraryPlate,
    LibraryPlate,
)
from covid_database.populate.base import BaseDriveFolderPopulator
from covid_database.populate.sequencing_tracking_populators.utils import check_control
from covidhub.config import Config
from covidhub.google.drive import DriveService

log = logging.getLogger(__name__)


class LibraryPlatePopulator(BaseDriveFolderPopulator):
    """
    Class that populates all relevant data from the library plate metadata drive folder

    Parameters
    ----------
    :param session: An open DB session object
    :param config: Config instance
    :param drive_service: An authenticated gdrive service object
    """

    def __init__(self, session: Session, drive_service: DriveService, cfg: Config):
        library_plate_folder = (
            cfg.INPUT_GDRIVE_PATH + cfg["DATA"]["library_plate_layout_folder"]
        )
        super().__init__(
            session=session,
            drive_service=drive_service,
            folder_path_components=library_plate_folder,
        )

    @property
    def models_to_populate(self) -> List[str]:
        """The models that the LibraryPlatePopulator will create and inset into the DB"""
        return [LibraryPlate.__name__, CZBIDLibraryPlate.__name__]

    def populate_models(self):
        # get all existing lib plate barcodes
        existing_lib_id_models = self.session.query(LibraryPlate).all()
        existing_lib_plate_barcodes = {
            result.barcode for result in existing_lib_id_models
        }

        log.info("populating library plate metadata")
        library_plate_map_files = self.load_files(file_ext=".csv")
        for library_plate_map_file in library_plate_map_files:
            library_plate_map_data = pd.read_csv(library_plate_map_file.data)
            plate_barcode = library_plate_map_file.filename.split(".")[0]
            if plate_barcode in existing_lib_plate_barcodes:
                continue
            library_plate_model = LibraryPlate(barcode=plate_barcode)
            self.session.add(library_plate_model)

            czb_ids_well_id = (
                library_plate_map_data[["CZB_ID", "Unnamed: 0"]].dropna().values
            )
            for czb_id, well_id in czb_ids_well_id:
                # check if czb_id exists
                czb_id = czb_id.split("_W")[0]
                czb_id_model = (
                    self.session.query(CZBID)
                    .filter(CZBID.czb_id == czb_id)
                    .one_or_none()
                )
                if czb_id_model is None:
                    if czb_id != "nan" and not check_control(czb_id):
                        log.error(f"no czb_id entry found for {czb_id}")
                    continue
                if well_id and len(well_id) == 3 and well_id[1] == "0":
                    # remove instance where well id is formatted like A01 instead of A1
                    well_id = f"{well_id[0]}{well_id[2]}"

                self.session.add(
                    CZBIDLibraryPlate(
                        czb_id_id=czb_id_model.id,
                        library_plate=library_plate_model,
                        well_id=well_id,
                    )
                )
