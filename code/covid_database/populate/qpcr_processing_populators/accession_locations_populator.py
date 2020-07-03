import logging
from typing import List

import pandas as pd
from sqlalchemy.orm import Session

from covid_database.models.qpcr_processing import AccessionSample, LocationFileChecksums
from covid_database.populate.base import BaseDriveFolderPopulator
from covidhub.config import Config
from covidhub.google.drive import DriveService

log = logging.getLogger(__name__)


class AccessionLocationsPopulator(BaseDriveFolderPopulator):
    """
    Class that populates all relevant data from the Accessions Locations drive folder

     Parameters
    ----------
    :param session: An open DB session object
    :param config: Config instance
    :param drive_service: An authenticated gdrive service object
    """

    def __init__(self, session: Session, drive_service: DriveService, cfg: Config):
        super().__init__(
            session=session,
            drive_service=drive_service,
            folder_path_components=cfg.ACCESSION_LOCATIONS_FOLDER,
        )

    @property
    def models_to_populate(self) -> List[str]:
        """
        The models that the PlateLayoutPopulator will create and insert into the DB
        """
        return []  # this populator modifies but does not create models

    def populate_models(self):
        """Create all models and insert into DB"""
        log.info("populating accessions and accession samples")

        existing_checksums = {
            result.csv_checksum for result in self.session.query(LocationFileChecksums)
        }

        accession_location_files = self.load_files(
            file_ext=".csv", checksums=existing_checksums
        )

        processed_accessions = set()
        for location_file in accession_location_files:
            for idx, row in pd.read_csv(location_file.data).iterrows():
                accession = row["Accession"]
                if accession in processed_accessions:
                    continue

                location = row["Loc"]
                submitter_id = row["Submitter_ID"] if "Submitter_ID" in row else None

                # get entry
                accession_models = (
                    self.session.query(AccessionSample)
                    .filter(AccessionSample.accession == accession)
                    .all()
                )

                for model in accession_models:
                    model.location = location
                    model.submitter_id = submitter_id

                processed_accessions.add(accession)
                self.session.add(
                    LocationFileChecksums(csv_checksum=location_file.md5Checksum)
                )
