import logging
import re
from typing import List, TextIO

from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound

from covid_database.models.enums import ControlType
from covid_database.models.qpcr_processing import AccessionSample, SamplePlate
from covid_database.populate.base import BaseDriveFolderPopulator
from covidhub.config import Config
from covidhub.constants import VALID_ACCESSION
from covidhub.google.drive import DriveService
from qpcr_processing.accession import get_plate_map_type_from_name, read_accession_data
from qpcr_processing.accession_tracking.accession_tracking import (
    extract_barcode_from_plate_map_filename,
)

log = logging.getLogger(__name__)
CONTROL_TYPES = {item.value for item in ControlType}


class PlateLayoutPopulator(BaseDriveFolderPopulator):
    """
    Class that populates all relevant data from the plate layout drive folder

     Parameters
    ----------
    :param session: An open DB session object
    :param config: Config instance
    :param drive_service: An authenticated gdrive service object
    """

    def __init__(self, session: Session, drive_service: DriveService, cfg: Config):
        plate_layout_folder_components = cfg.PLATE_LAYOUT_FOLDER
        super().__init__(
            session=session,
            drive_service=drive_service,
            folder_path_components=plate_layout_folder_components,
        )

    @property
    def models_to_populate(self) -> List[str]:
        """
        The models that the PlateLayoutPopulator will create and insert into the DB
        """
        return [AccessionSample.__name__]

    def populate_models(self):
        """Create all models and insert into DB"""
        log.info("populating accession samples")

        existing_checksums = {
            sample_plate.plate_layout_checksum
            for sample_plate in self.session.query(SamplePlate)
        }

        accession_files = self.load_files(file_ext=".csv", checksums=existing_checksums)

        for accession_file in accession_files:
            self.insert_accessions_and_accession_samples_from_accession_file(
                accession_file.filename,
                accession_file.md5Checksum,
                accession_file.data,
            )

        self.session.flush()

    def insert_accessions_and_accession_samples_from_accession_file(
        self, accession_filename: str, accession_checksum: str, accession_fh: TextIO
    ):
        """Creates all models from a specific plate layout file"""
        log.debug(f"Reading layout file {accession_filename}")

        plate_map_type = get_plate_map_type_from_name(accession_filename)
        sample_plate_barcode = extract_barcode_from_plate_map_filename(
            accession_filename, plate_map_type
        )
        # get sample plate entry from DB
        try:
            plate_model = (
                self.session.query(SamplePlate)
                .filter(SamplePlate.barcode == sample_plate_barcode)
                .one()
            )
        except NoResultFound:
            log.critical(
                f"Did not find entry for sample plate {sample_plate_barcode} from "
                f"file {accession_filename}",
                extra={"notify_slack": True},
            )
            return

        try:
            accession_data = read_accession_data(plate_map_type, accession_fh)
        except Exception:
            log.critical(
                f"Error reading {accession_filename}", extra={"notify_slack": True}
            )
            log.exception("Details:")
            return

        plate_model.plate_layout_checksum = accession_checksum
        plate_model.accessions.clear()
        self.session.flush()

        for well_id, value in accession_data.items():
            if re.fullmatch(VALID_ACCESSION, value):
                accession_sample = AccessionSample(
                    accession=value, sample_plate=plate_model, well_id=well_id,
                )
                self.session.add(accession_sample)
