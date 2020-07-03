import logging
from typing import List

import pandas as pd
from sqlalchemy.orm import Session

from covid_database.models.ngs_sample_tracking import (
    CZBID,
    CZBIDOgPlate,
    CZBIDThaw,
    DphCZBID,
    OgPlate,
    QPCRCollaboratorCqValue,
)
from covid_database.populate.base import BaseDriveFolderPopulator
from covid_database.populate.sequencing_tracking_populators.utils import check_control
from covidhub.config import Config
from covidhub.google.drive import DriveService

log = logging.getLogger(__name__)

LEGACY_HEADER_1_MAP = {
    "type": "legacy",
    "container_name": "Original_Box_Name",
    "date_received": "Date_Received",
    "accession_id": "Accession_ID",
    "plate_name": "Plate_Name",
    "well_id": "Plate_Well_Location",
    "initial_volume": "Volume",
    "comments": "Comments",
    "czb_id": "CZB_ID",
}

LEGACY_HEADER_2_MAP = {
    "type": "legacy",
    "container_name": "Original_Bag_Name",
    "date_received": "Date_Received",
    "accession_id": "Accession_ID",
    "date_on_tube": "Date_On_Tube",
    "plate_name": "Plate_Name",
    "well_id": "Plate_Well_Location",
    "initial_volume": "Volume_uL",
    "beads": "Beads",
    "comments": "Comments",
    "czb_id": "CZB_ID",
}

HEADER_MAP = {
    "type": "current",
    "container_name": "Original_Container_Name",
    "date_received": "Date_Container_Received",
    "date_og_plate_created": "Date_OG_Plate_made",
    "created_by": "OG_Plate_Makers",
    "specimen_type": "Source_Specimen_Type",
    "accession_id": "Accession_ID",
    "plate_name": "OG_Plate_Name",
    "well_id": "OG_Plate_Well_Location",
    "initial_volume": "Sample_Volume",
    "czb_id": "CZB_ID",
    "call": "Call",
    "ct_1": "CT_1",
    "ct_2": "CT_2",
    "ct_3": "CT_3",
    "comments": "Comments",
    "ct_host": "CT_Host",
    "ct_def": "CT_Def",
    "extraction_method": "Extraction_Method",
}

HEADERS_MAP = {
    "Original_Box_Name": LEGACY_HEADER_1_MAP,
    "Original_Bag_Name": LEGACY_HEADER_2_MAP,
    "Original_Container_Name": HEADER_MAP,
}


class OGPlateMetadataPopulator(BaseDriveFolderPopulator):
    """
    Class that populates all relevant data from the og plate metadata drive folder

    Parameters
    ----------
    :param session: An open DB session object
    :param config: Config instance
    :param drive_service: An authenticated gdrive service object
    """

    def __init__(self, session: Session, drive_service: DriveService, cfg: Config):
        og_plate_metadata_folder = (
            cfg.INPUT_GDRIVE_PATH + cfg["DATA"]["og_plate_metadata_folder"]
        )
        super().__init__(
            session=session,
            drive_service=drive_service,
            folder_path_components=og_plate_metadata_folder,
        )

    @property
    def models_to_populate(self) -> List[str]:
        """
        The models that the OGPlateMetadataPopulator will create and inset into the DB.
        """
        return [
            DphCZBID.__name__,
            CZBIDOgPlate.__name__,
            QPCRCollaboratorCqValue.__name__,
        ]

    def populate_models(self):
        log.info("populating og plate models")
        og_metadata_files = self.load_files(file_ext=".xlsx")

        existing_og_plate_models = self.session.query(OgPlate).all()
        existing_og_plate_barcodes = {
            result.barcode for result in existing_og_plate_models
        }

        for og_metadata_file in og_metadata_files:
            og_metadata_file_data = pd.read_excel(og_metadata_file.data)
            first_column_name = og_metadata_file_data.columns[0]
            if first_column_name == "Unnamed: 0":
                continue
            column_header_map = HEADERS_MAP[first_column_name]
            og_plate = self.add_og_plate(
                og_metadata_file_data, column_header_map, existing_og_plate_barcodes
            )
            if not og_plate:
                continue
            og_plate_czb_ids = set(
                og_metadata_file_data[column_header_map["czb_id"]].dropna().values
            )
            for czb_id in og_plate_czb_ids:
                if check_control(czb_id):
                    continue
                czb_id_model = (
                    self.session.query(CZBID)
                    .filter(CZBID.czb_id == czb_id)
                    .one_or_none()
                )
                if not czb_id_model:
                    log.info(f"did not find {czb_id}")
                    continue
                self.add_collaborator_results(
                    column_header_map, czb_id_model, og_metadata_file_data
                )
                try:
                    # Add czbid_to_og_plate entry
                    self.add_czb_id_to_og_plate(
                        column_header_map, czb_id_model, og_metadata_file_data, og_plate
                    )
                except Exception as e:
                    log.critical(
                        f"Could not add plate and entries from {og_metadata_file.filename}: {e}"
                    )

    def add_og_plate(
        self, og_metadata_file_data, column_header_map, existing_og_plate_barcodes
    ):
        date_created = None
        created_by = None
        plate_name = set(
            og_metadata_file_data[column_header_map["plate_name"]].dropna()
        ).pop()
        if plate_name in existing_og_plate_barcodes:
            return
        if column_header_map["type"] == "current":
            # this info only available in current files
            date_created = set(
                og_metadata_file_data[
                    column_header_map["date_og_plate_created"]
                ].dropna()
            )
            date_created = date_created.pop() if len(date_created) != 0 else None
            created_by = set(
                og_metadata_file_data[column_header_map["created_by"]].dropna()
            )
            created_by = created_by.pop() if len(created_by) != 0 else None
        og_plate = OgPlate(
            barcode=plate_name, created_by=created_by, created_date=date_created
        )
        self.session.add(og_plate)
        self.session.flush()
        existing_og_plate_barcodes.add(plate_name)
        return og_plate

    def add_czb_id_to_og_plate(
        self, column_header_map, czb_id, og_metadata_file_data, og_plate
    ):
        well_id = self.get_info_for_czb_id(
            og_metadata_file_data, "well_id", czb_id.czb_id, column_header_map
        )
        if well_id and len(well_id) == 3 and well_id[1] == "0":
            # remove instance where well id is formatted like A01 instead of A1
            well_id = f"{well_id[0]}{well_id[2]}"

        model = (
            self.session.query(CZBIDOgPlate)
            .filter(CZBIDOgPlate.czb_id == czb_id)
            .one_or_none()
        )
        if model:
            log.info(
                f"Already have czb_id model for {czb_id.czb_id}, on plate {model.og_plate}, going to delete this model in favor of"
                f"{og_plate}"
            )
            self.session.delete(model)
            self.session.flush()

        czb_id_to_og_plate = CZBIDOgPlate(
            czb_id=czb_id, og_plate=og_plate, well_id=well_id,
        )
        self.session.add(czb_id_to_og_plate)
        # add an initial thaw
        self.session.add(CZBIDThaw(czb_id_id=czb_id.id))

    def get_info_for_czb_id(
        self, og_metadata_file_data, column_name, czb_id, column_header_map
    ):
        value = list(
            og_metadata_file_data.loc[
                og_metadata_file_data[column_header_map["czb_id"]] == czb_id
            ][column_header_map[column_name]].values
        )
        if len(value) == 0 or pd.isna(value[0]) or value[0] == "ND":
            return None
        return value[0]

    def add_collaborator_results(
        self, column_header_map, czb_id, og_metadata_file_data
    ):
        # add collaborator results
        if column_header_map["type"] == "current":
            gene_names = self.get_info_for_czb_id(
                og_metadata_file_data, "ct_def", czb_id.czb_id, column_header_map
            )
            if not gene_names:
                # no ct def
                return
            gene_names = gene_names.split("_")
            gene1, gene2, gene3, ct_hostname = (
                gene_names[0],
                gene_names[1],
                gene_names[2],
                gene_names[3],
            )
            # create cq values
            cq1_value = self.get_info_for_czb_id(
                og_metadata_file_data, "ct_1", czb_id.czb_id, column_header_map
            )
            cq2_value = self.get_info_for_czb_id(
                og_metadata_file_data, "ct_2", czb_id.czb_id, column_header_map
            )
            cq3_value = self.get_info_for_czb_id(
                og_metadata_file_data, "ct_3", czb_id.czb_id, column_header_map
            )
            cq_host_value = self.get_info_for_czb_id(
                og_metadata_file_data, "ct_host", czb_id.czb_id, column_header_map
            )
            self.session.add(
                QPCRCollaboratorCqValue(
                    czb_id_id=czb_id.id, gene_value=gene1, cq_value=cq1_value,
                )
            )
            self.session.add(
                QPCRCollaboratorCqValue(
                    czb_id_id=czb_id.id, gene_value=gene2, cq_value=cq2_value,
                )
            )
            self.session.add(
                QPCRCollaboratorCqValue(
                    czb_id_id=czb_id.id, gene_value=gene3, cq_value=cq3_value,
                )
            )
            self.session.add(
                QPCRCollaboratorCqValue(
                    czb_id_id=czb_id.id,
                    gene_value=ct_hostname,
                    cq_value=cq_host_value,
                    host=True,
                )
            )
            self.session.flush()
