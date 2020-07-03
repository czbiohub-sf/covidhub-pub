import logging
from typing import List, TextIO, Tuple

from sqlalchemy.orm import Session

from covid_database.models.qpcr_processing import (
    FluorValue,
    QPCRPlate,
    QPCRResult,
    QPCRRun,
    SamplePlate,
)
from covid_database.populate.base import BaseDriveFolderPopulator
from covidhub.config import Config
from covidhub.constants import Fluor, MappedWell
from covidhub.google.drive import DriveService
from qpcr_processing.processing_results import ProcessingResults
from qpcr_processing.protocol import get_protocol

log = logging.getLogger(__name__)


class QPCRResultsPopulator(BaseDriveFolderPopulator):
    """
    Class that populates qpcr results related data

    Parameters
    ----------
    session :
        An open DB session object
    drive_service :
        An authenticated gdrive service object
    cfg :
        An initialized Config object to read path components from
    """

    def __init__(self, session: Session, drive_service: DriveService, cfg: Config):
        csv_results_folder = cfg.CSV_RESULTS_FOLDER_TRACKING
        self.cfg = cfg
        super().__init__(
            session=session,
            drive_service=drive_service,
            folder_path_components=csv_results_folder,
        )

    @property
    def models_to_populate(self) -> List[str]:
        """The models that the PlateLayoutPopulator will create and inset into the DB"""
        return [QPCRResult.__name__, FluorValue.__name__]

    @staticmethod
    def extract_barcodes_from_filename(filename) -> Tuple[str, str]:
        """return the sample plate barcdoe and pcr barcode from the results.csv filename"""
        filename_parts = filename.split("-")
        sample_barcode = filename_parts[0]
        pcr_barcode = filename_parts[1]
        return sample_barcode, pcr_barcode

    def get_plate_models(self, sample_barcode, pcr_barcode):
        """Check if the sample and pcr plates exist for the results and if we've already processed
        the run, if so return False."""
        sample_plate = (
            self.session.query(SamplePlate)
            .filter(SamplePlate.barcode == sample_barcode)
            .one_or_none()
        )
        pcr_plate = (
            self.session.query(QPCRPlate)
            .filter(QPCRPlate.barcode == pcr_barcode)
            .one_or_none()
        )
        return sample_plate, pcr_plate

    def populate_models(self):
        """Create all models and insert into DB"""
        log.info("populating qpcr runs and results")

        existing_checksums = {
            qpcr_run.csv_checksum for qpcr_run in self.session.query(QPCRRun)
        }

        csv_files = self.load_files(file_ext=".csv", checksums=existing_checksums)

        for csv_file in csv_files:
            self.insert_qpcr_results(
                csv_file.filename, csv_file.md5Checksum, csv_file.data,
            )
        self.session.flush()

    def insert_qpcr_results(self, csv_filename: str, checksum: str, csv_data: TextIO):
        """Check that all necessary info is in the DB to process this sample
        if so, insert the corresponding QPCRResult and Fluor models"""
        (
            sample_barcode,
            pcr_barcode,
        ) = QPCRResultsPopulator.extract_barcodes_from_filename(csv_filename)
        sample_plate = (
            self.session.query(SamplePlate)
            .filter(SamplePlate.barcode == sample_barcode)
            .one_or_none()
        )
        if not sample_plate:
            log.critical(
                f"Did not find sample plate entry for {sample_barcode}, skipping",
                extra={"notify_slack": True},
            )
            return
        pcr_plate = (
            self.session.query(QPCRPlate)
            .filter(QPCRPlate.barcode == pcr_barcode)
            .one_or_none()
        )
        if not pcr_plate:
            log.critical(
                f"Did not find qpcr plate entry for {pcr_barcode}, skipping",
                extra={"notify_slack": True},
            )
            return
        qpcr_run = (
            self.session.query(QPCRRun)
            .filter(QPCRRun.qpcr_plate == pcr_plate)
            .one_or_none()
        )
        if not qpcr_run:
            log.critical(
                f"Did not find qpcr run entry for barcode {pcr_barcode}, skipping",
                extra={"notify_slack": True},
            )
            return

        protocol = get_protocol(qpcr_run.protocol.value)
        try:
            processing_results = ProcessingResults.from_results_file(
                fh=csv_data, protocol=protocol
            )
        except ValueError:
            log.error(f"Failed to read results from {csv_filename}, skipping")
            return

        qpcr_run.completed_at = processing_results.completion_time
        qpcr_run.csv_checksum = checksum
        qpcr_run.qpcr_results.clear()

        try:
            log.debug(
                f"Creating processing results models from {csv_filename}, using "
                f"protocol {protocol.name}"
            )
            for well_id, well_result in processing_results.well_results.items():
                qpcr_result = QPCRResult(
                    well_id=well_id,
                    control_type=well_result.control_type,
                    call=well_result.call,
                    qpcr_run=qpcr_run,
                )
                self.session.add(qpcr_result)
                for fluor, genes_positions in protocol.mapping.items():
                    fluor = Fluor(fluor)
                    for pos, gene in genes_positions.items():
                        if gene not in protocol.gene_list:
                            # skip other genes
                            continue
                        position = MappedWell(pos)
                        cq_value = well_result.gene_cts[gene]
                        cq_value = float("NAN") if not cq_value else cq_value
                        fluor_val = FluorValue(
                            qpcr_result=qpcr_result,
                            fluor=fluor,
                            position=position,
                            cq_value=cq_value,
                        )
                        self.session.add(fluor_val)
        except Exception as e:
            log.error(
                f"Error occurred while adding results for {sample_barcode}-{pcr_barcode}: {e}"
            )
