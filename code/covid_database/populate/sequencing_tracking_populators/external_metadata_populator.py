import logging
from typing import List

import pandas as pd
from sqlalchemy.orm import Session

from covid_database.models.enums import NGSProjectType
from covid_database.models.ngs_sample_tracking import CollaboratorCZBID, CZBID, DphCZBID
from covid_database.populate.base import BaseDriveFolderPopulator
from covid_database.populate.sequencing_tracking_populators.utils import ProjectHandler
from covidhub.config import Config
from covidhub.constants.comet_forms import CollaboratorSampleMetadata, DPHSampleMetadata
from covidhub.google.drive import DriveService

log = logging.getLogger(__name__)


class ExternalMetadataPopulator(BaseDriveFolderPopulator):
    """
    Class that populates all relevant data from the external metadata update files drive folder

    Parameters
    ----------
    :param session: An open DB session object
    :param config: Config instance
    :param drive_service: An authenticated gdrive service object
    """

    def __init__(self, session: Session, drive_service: DriveService, cfg: Config):
        external_metadata_folder = (
            cfg.INPUT_GDRIVE_PATH + cfg["DATA"]["comet_form0_update_files_folder"]
        )
        super().__init__(
            session=session,
            drive_service=drive_service,
            folder_path_components=external_metadata_folder,
        )

    def models_to_populate(self) -> List[str]:
        """The models that the OGPlateMetadataPopulator will create and inset into the DB"""
        return [DphCZBID.__name__, CollaboratorCZBID.__name__]

    def populate_models(self):
        # get all existing czb_ids
        existing_czb_id_models = self.session.query(CZBID).all()
        existing_czb_ids = {result.czb_id for result in existing_czb_id_models}

        log.info("populating registered external samples")
        projects_handler = ProjectHandler(session=self.session)

        registered_samples_files = self.load_files(file_ext=".csv")

        for registered_samples_file in registered_samples_files:
            registered_samples_data = pd.read_csv(registered_samples_file.data)
            for _, row in registered_samples_data.iterrows():
                if row["CZB_ID"] in existing_czb_ids:
                    continue
                project = projects_handler.get_project_from_czb_id(czb_id=row["CZB_ID"])
                if project.type == NGSProjectType.DPH:
                    self.session.add(
                        DphCZBID(
                            project_id=project.id,
                            czb_id=row[DPHSampleMetadata.CZB_ID],
                            initial_volume=row[DPHSampleMetadata.INITIAL_VOLUME],
                            external_accession=row[
                                DPHSampleMetadata.EXTERNAL_ACCESSION
                            ],
                            collection_date=row[DPHSampleMetadata.COLLECTION_DATE],
                            zip_prefix=row[DPHSampleMetadata.ZIP_PREFIX],
                            container_name=row[DPHSampleMetadata.CONTAINER_NAME],
                            extraction_method=row[DPHSampleMetadata.EXTRACTION_METHOD],
                            specimen_source=row[DPHSampleMetadata.SPECIMEN_TYPE],
                            date_received=row[DPHSampleMetadata.DATE_RECEIVED],
                        )
                    )
                if project.type == NGSProjectType.OTHER:
                    self.session.add(
                        CollaboratorCZBID(
                            project_id=project.id,
                            czb_id=row[CollaboratorSampleMetadata.CZB_ID],
                            initial_volume=row[
                                CollaboratorSampleMetadata.INITIAL_VOLUME
                            ],
                            external_accession=row[
                                CollaboratorSampleMetadata.EXTERNAL_ACCESSION
                            ],
                            collection_date=row[
                                CollaboratorSampleMetadata.COLLECTION_DATE
                            ],
                            specimen_source=row[
                                CollaboratorSampleMetadata.SPECIMEN_TYPE
                            ],
                        )
                    )
