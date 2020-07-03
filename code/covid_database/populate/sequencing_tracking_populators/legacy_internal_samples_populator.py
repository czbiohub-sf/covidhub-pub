import logging
from typing import List

import pandas as pd
from sqlalchemy.orm import Session

from covid_database.models.enums import NGSProjectType
from covid_database.models.ngs_sample_tracking import (
    CZBID,
    CZBIDRnaPlate,
    InternalCZBID,
)
from covid_database.models.qpcr_processing import RNAPlate
from covid_database.populate.base import BaseDriveFolderPopulator
from covid_database.populate.sequencing_tracking_populators.utils import ProjectHandler
from covidhub.config import Config
from covidhub.google.drive import DriveService

log = logging.getLogger(__name__)


class LegacyInternalSamplesPopulator(BaseDriveFolderPopulator):
    """
    Class that populates all relevant data from the og plate metadata drive folder

    Parameters
    ----------
    :param session: An open DB session object
    :param config: Config instance
    :param drive_service: An authenticated gdrive service object
    """

    def __init__(self, session: Session, drive_service: DriveService, cfg: Config):
        legacy_samples_folder = (
            cfg.INPUT_GDRIVE_PATH + cfg["DATA"]["legacy_internal_samples_folder"]
        )
        super().__init__(
            session=session,
            drive_service=drive_service,
            folder_path_components=legacy_samples_folder,
        )

    def models_to_populate(self) -> List[str]:
        """The models that the OGPlateMetadataPopulator will create and inset into the DB"""
        return [InternalCZBID.__name__, CZBIDRnaPlate.__name__]

    def populate_models(self):
        # get all existing czb_ids
        existing_czb_id_models = self.session.query(CZBID).all()
        existing_czb_ids = {result.czb_id for result in existing_czb_id_models}

        log.info("populating legacy internal samples")
        legacy_internal_sample_files = self.load_files(file_ext=".xlsx")

        projects_handler = ProjectHandler(session=self.session)
        for legacy_internal_sample_file in legacy_internal_sample_files:
            legacy_internal_sample_data = pd.read_excel(
                legacy_internal_sample_file.data
            )
            czb_ids = set(legacy_internal_sample_data["CZB_ID"].dropna())
            for czb_id in czb_ids:
                if czb_id in existing_czb_ids:
                    # updates only
                    continue
                project = projects_handler.get_project_from_czb_id(czb_id=czb_id)
                if not project:
                    log.error(
                        f"czb_id: {czb_id}, does not match and existing project rr codes"
                    )
                    # continue
                if project.type != NGSProjectType.INTERNAL:
                    continue
                if project.type == NGSProjectType.INTERNAL:
                    czb_id_model = InternalCZBID(czb_id=czb_id, project_id=project.id)
                    self.session.add(czb_id_model)
                    self.session.flush()
                    if "96 RNA Plate Barcode" in legacy_internal_sample_data:
                        rna_plate_barcode = list(
                            legacy_internal_sample_data.loc[
                                legacy_internal_sample_data["CZB_ID"] == czb_id
                            ]["96 RNA Plate Barcode"].values
                        )
                        if len(rna_plate_barcode) == 0 or pd.isna(rna_plate_barcode[0]):
                            log.error(f"No rna plate info for {czb_id}")
                        else:
                            rna_plate_barcode = rna_plate_barcode[0]
                            if rna_plate_barcode.lower() == "water":
                                continue
                            rna_plate_model = (
                                self.session.query(RNAPlate)
                                .filter(RNAPlate.barcode == rna_plate_barcode)
                                .one_or_none()
                            )
                            well = list(
                                legacy_internal_sample_data.loc[
                                    legacy_internal_sample_data["CZB_ID"] == czb_id
                                ]["Well"].values
                            )[0]
                            if not rna_plate_model:
                                log.error(
                                    f"Did not find entry for barcode {rna_plate_barcode}"
                                )
                                continue
                            self.session.add(
                                CZBIDRnaPlate(
                                    czb_id_id=czb_id_model.id,
                                    rna_plate_id=rna_plate_model.id,
                                    well_id=well,
                                )
                            )

        # # finally populate from the angela csv
        manual_legacy_internal_sample_files = self.load_files(file_ext=".csv")
        for manual_legacy_internal_sample_file in manual_legacy_internal_sample_files:
            legacy_internal_sample_data = pd.read_csv(
                manual_legacy_internal_sample_file.data
            )
            important_info = [
                list(v)
                for v in list(
                    legacy_internal_sample_data[
                        ["CZB_ID", "96 RNA Plate Barcode", "Well"]
                    ].values
                )
            ]
            for czb_id, rna_plate_barcode, well_id in important_info:
                if czb_id in existing_czb_ids or rna_plate_barcode.lower() == "water":
                    # updates only
                    continue
                rna_plate_model = (
                    self.session.query(RNAPlate)
                    .filter(RNAPlate.barcode == rna_plate_barcode)
                    .one_or_none()
                )
                if not rna_plate_model:
                    log.error(f"Did not find entry for barcode {rna_plate_barcode}")
                    continue
                # check for existing CZBID
                czb_id_model = (
                    self.session.query(CZBID)
                    .filter(CZBID.czb_id == czb_id)
                    .one_or_none()
                )
                if not czb_id_model:
                    log.error(f"No exisiting model for czb_id {czb_id}")
                    continue
                # check for czb_id_to_rna_plate_model
                czb_id_to_rna_plate_model = (
                    self.session.query(CZBIDRnaPlate)
                    .filter(CZBIDRnaPlate.czb_id_id == czb_id_model.id)
                    .one_or_none()
                )
                if czb_id_to_rna_plate_model:
                    # already added info, can skip
                    continue
                if pd.isna(well_id):
                    log.error(f"no well info found for czb_id: {czb_id}")
                    continue

                # check for rna plate
                self.session.add(
                    CZBIDRnaPlate(
                        czb_id_id=czb_id_model.id,
                        rna_plate_id=rna_plate_model.id,
                        well_id=well_id,
                    )
                )
