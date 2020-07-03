import logging
from typing import List

import pandas as pd
from sqlalchemy.orm import Session

from covid_database.models.ngs_sample_tracking import CollaboratorCZBID, CZBID, DphCZBID
from covid_database.populate.base import BaseDriveFolderPopulator
from covid_database.populate.sequencing_tracking_populators.utils import ProjectHandler
from covidhub.config import Config
from covidhub.google.drive import DriveService

log = logging.getLogger(__name__)


class LegacyExternalMetadataPopulator(BaseDriveFolderPopulator):
    """
    Class that populates all relevant data from the external metadata drive folder

    Parameters
    ----------
    session:
        An open DB session object
    cfg:
        Config instance
    drive_service:
        An authenticated gdrive service object
    """

    DPH_FILENAME = "dph_czb_ids.csv"
    COLLABORATOR_FILENAME = "collaborator_czb_ids.csv"

    def __init__(self, session: Session, drive_service: DriveService, cfg: Config):
        self.external_metadata_folder = (
            cfg.INPUT_GDRIVE_PATH + cfg["DATA"]["legacy_external_metadata_folder"]
        )
        super().__init__(
            session=session,
            drive_service=drive_service,
            folder_path_components=self.external_metadata_folder,
        )

    def models_to_populate(self) -> List[str]:
        """The models that the OGPlateMetadataPopulator will create and inset into the DB"""
        return [DphCZBID.__name__, CollaboratorCZBID.__name__]

    def _normalize_value(self, row_val):
        return row_val if not pd.isna(row_val) else None

    def populate_models(self):
        # get all existing czb_ids
        existing_czb_id_models = self.session.query(CZBID).all()
        existing_czb_ids = {result.czb_id for result in existing_czb_id_models}

        # load the files.
        files = self.load_files(
            names={
                LegacyExternalMetadataPopulator.DPH_FILENAME,
                LegacyExternalMetadataPopulator.COLLABORATOR_FILENAME,
            }
        )
        dph = [
            file
            for file in files
            if file.filename == LegacyExternalMetadataPopulator.DPH_FILENAME
        ][0]
        collaborator = [
            file
            for file in files
            if file.filename == LegacyExternalMetadataPopulator.COLLABORATOR_FILENAME
        ][0]

        log.info("populating legacy dph samples")
        projects_handler = ProjectHandler(session=self.session)
        legacy_dph_samples_data = pd.read_csv(dph.data)
        for idx, row in legacy_dph_samples_data.iterrows():
            project = projects_handler.get_project_from_czb_id(czb_id=row["czb_id"])
            if row["czb_id"] in existing_czb_ids:
                continue
            self.session.add(
                DphCZBID(
                    project_id=project.id,
                    czb_id=row["czb_id"],
                    initial_volume=row["initial_volume"],
                    external_accession=row["external_accession"],
                    specimen_source=row["specimen_source"],
                    collection_date=self._normalize_value(row["collection_date"]),
                    tested_date=self._normalize_value(row["tested_date"]),
                    zip_prefix=self._normalize_value(row["zip_prefix"]),
                    extraction_method=row["extraction_method"],
                    container_name=row["container_name"],
                    date_received=self._normalize_value(row["date_received"]),
                )
            )

        log.info("populating legacy collaborator samples")
        legacy_colab_samples_data = pd.read_csv(collaborator.data)
        for idx, row in legacy_colab_samples_data.iterrows():
            project = projects_handler.get_project_from_czb_id(czb_id=row["czb_id"])
            if row["czb_id"] in existing_czb_ids or row["czb_id"] == "water_control":
                continue
            self.session.add(
                CollaboratorCZBID(
                    project_id=project.id,
                    czb_id=row["czb_id"],
                    initial_volume=row["initial_volume"],
                    external_accession=row["external_accession"],
                    specimen_source=row["specimen_source"],
                    collection_date=self._normalize_value(row["collection_date"]),
                    zip_prefix=self._normalize_value((row["zip_prefix"])),
                )
            )
