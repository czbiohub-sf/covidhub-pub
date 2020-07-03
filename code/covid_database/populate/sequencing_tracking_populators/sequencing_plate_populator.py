import abc
import logging
from typing import List, Set
from urllib.parse import parse_qs, urlparse

import pandas as pd
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session

from covid_database.models.ngs_sample_tracking import (
    CZBIDLibraryPlate,
    LibraryPlate,
    SequencingPlateCreation,
)
from covid_database.populate.base import (
    BaseWorksheetPopulator,
    RemoteWorksheetPopulatorMixin,
)
from covidhub.config import Config
from covidhub.google import drive

log = logging.getLogger(__name__)


class SequencingPlatesPopulator(BaseWorksheetPopulator):
    """
    Class that populates all COMET sequencing plates.
    """

    @abc.abstractmethod
    def get_index_data_from_url(self, index_plate_urls: Set[str]) -> pd.DataFrame:
        ...

    @property
    def models_to_populate(self) -> List[str]:
        """The models that the SequencingPlatesPopulator will create and inset into the DB"""
        return []

    def populate_models(self):
        """Create all models and insert into DB"""
        existing_seq_plate_lib_id_models = self.session.query(
            SequencingPlateCreation
        ).all()
        existing_seq_plate_creation_lib_ids = {
            result.library_plate_id for result in existing_seq_plate_lib_id_models
        }

        log.info("Adding sequencing index info")
        seq_plate_barcodes = set(
            self.data["COMET 384 Sequencing Plate Barcode"].dropna()
        )
        for seq_plate_barcode in seq_plate_barcodes:
            lib_plate_model = (
                self.session.query(LibraryPlate)
                .filter(LibraryPlate.barcode == seq_plate_barcode)
                .one_or_none()
            )
            if not lib_plate_model:
                log.error(f"No library plate found for barcode {seq_plate_barcode}")
                continue
            if lib_plate_model.id in existing_seq_plate_creation_lib_ids:
                continue
            created_date = list(
                self.data.loc[
                    self.data["COMET 384 Sequencing Plate Barcode"] == seq_plate_barcode
                ]["Timestamp"].dropna()
            )
            created_date = created_date[0] if len(created_date) != 0 else None
            self.session.add(
                SequencingPlateCreation(
                    created_date=created_date, library_plate_id=lib_plate_model.id
                )
            )
            urls = set(
                self.data[
                    self.data["COMET 384 Sequencing Plate Barcode"] == seq_plate_barcode
                ]["COMET 384 Index Plate"].dropna()
            )
            index_data = self.get_index_data_from_url(urls)
            well_to_index_vals = [
                list(val)
                for val in index_data[
                    ["384_index", "i7_index_RC", "i5_index_RC"]
                ].values
            ]
            for well_id, i7_index, i5_index in well_to_index_vals:
                if well_id and len(well_id) == 3 and well_id[1] == "0":
                    # remove instance where well id is formatted like A01 instead of A1
                    well_id = f"{well_id[0]}{well_id[2]}"
                model = (
                    self.session.query(CZBIDLibraryPlate)
                    .filter(CZBIDLibraryPlate.library_plate_id == lib_plate_model.id)
                    .filter(CZBIDLibraryPlate.well_id == well_id)
                    .one_or_none()
                )
                if not model:
                    continue
                model.indexI5 = i5_index
                model.indexI7 = i7_index


class RemoteSequencingPlatesPopulator(
    RemoteWorksheetPopulatorMixin, SequencingPlatesPopulator
):
    """
    Class that populates all relevant data from the google worksheet COMET Index Plates
    """

    def __init__(
        self, session: Session, drive_service: drive.DriveService, cfg: Config,
    ):
        """
        Parameters
        ----------
        session : Session
            An open DB session object
        drive_service : DriveService
            An authenticated gdrive service object
        cfg : Config
            Config instance
        """
        super().__init__(session, drive_service, cfg)
        self.drive_service = drive_service

    @property
    def spreadsheet_id_config_key(self) -> str:
        return "mNGS_sample_tracking_form_responses_sheet_id"

    @property
    def sheet_name(self) -> str:
        return "COMET Index Plates"

    def get_index_data_from_url(self, index_plate_urls: Set[str]) -> pd.DataFrame:
        """Extracts the id parameter from a Google Drive URL and returns the file as a dataframe."""
        for url in index_plate_urls:
            file_id = parse_qs(urlparse(url).query)["id"][0]
            try:
                file = drive.find_file_by_id(self.drive_service, file_id)
                with file.open("rb") as fh:
                    return pd.read_excel(fh)
            except HttpError:
                continue
