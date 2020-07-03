import logging
import pathlib
import re
from typing import List, Optional

import pandas as pd

import covidhub.google.utils as gutils
from covidhub.collective_form import CollectiveForm
from covidhub.config import Config
from covidhub.constants import PlateMapType, VALID_ACCESSION
from covidhub.google import drive
from covidhub.google.drive import NoMatchesError
from covidhub.logging import create_logger
from qpcr_processing.accession import get_plate_map_type_from_name, read_accession_data
from qpcr_processing.accession_tracking.accession_tracking_data_store import (
    extract_all_barcodes_from_plate_layout_folder,
    extract_barcode_from_plate_map_filename,
    extract_timestamp_from_plate_map_filename,
    get_already_tracked_samples,
    ProcessingResources,
)
from qpcr_processing.accession_tracking.sample_tracker import SampleTracker

logger = logging.getLogger(__name__)

VERBOSE_SHEET_HEADER = [
    "Timestamp",
    "96 Sample Plate",
    "96 RNA Plate Barcode",
    "Location",
    "Submitter ID",
    "Well",
    "Accession",
    "Registered",
    "Checked Into Fridge",
    "Started RNA Extractions",
    "Checked into Freezer",
    "Completed RNA Extractions",
    "PCR Barcode",
    "Call",
    "qPCR Processing Complete",
    "E Cts",
    "N Cts",
    "RdRp Cts",
    "RNAse P Cts",
    "Resulted to CB",
]

CLIN_LAB_SHEET_HEADER = [
    "Registration Timestamp",
    "96 Sample Plate",
    "Well",
    "Accession",
    "Registered",
    "Started RNA Extraction",
    "PCR Barcode",
    "qPCR Processing Complete",
    "Processing Timestamp",
]

SUPERVISOR_PLATE_QUEUE_HEADER = [
    "Sample plate number",
    "Checked In time",
    "Checked in By",
    "Location in 4C",
    "Notes from sample plate metadata or sample arrival",
    "Ready to Process (yes if field G/H are empty, no if they are filled)",
    "Sample Started Processing time stamp",
    "Sample started processing by",
]


def accession_tracking_lambda_handler(event, context):
    cfg = Config()
    create_logger(cfg)
    accession_tracker = AccessionTracking(
        cfg=cfg, google_creds=gutils.get_secrets_manager_credentials()
    )
    accession_tracker.compile_accessions(updates_only=True)


def compile_accessions_cli(args):
    cfg = Config()
    create_logger(cfg, debug=args.debug)
    accession_tracker = AccessionTracking(
        cfg=cfg, google_creds=gutils.get_secrets_manager_credentials(args.secret_id)
    )
    accession_tracker.compile_accessions(
        sample_barcodes=args.sample_barcodes,
        run_path=args.run_path,
        updates_only=args.updates_only,
    )


class AccessionTracking:
    """
       Main processing loop for accession tracking:
       Grabs contents of accessions folder
       For each file:
           Generate sample tracking information for the associated 96 plate barcode
           Generate qPCR results about the given sample (if processed)
           For the supervisor plate queue sheet:
               Generate row for each sample that includes:
                   [
                       sample_barcode,
                       registered_time,
                       registered_by,
                       checked_into_fridge_location,
                       registration_notes,
                       ready_for_rna_extractions,
                       started_rna_extractions_time,
                       started_rna_extractions_by,
               ]
           For the verbose tracking sheet:
               Generate row for each accession that includes:
                   [
                       "Timestamp",
                       "96 Sample Plate",
                       "Well",
                       "Accession",
                       "Registered",
                       "Checked Into Fridge",
                       "Started RNA Extractions",
                       "Completed RNA Extractions",
                       "PCR Barcode",
                       "Call",
                       "qPCR Processing Complete",
                       "Resulted to CB",
                   ]
           For the Clin Lab tracking sheet:
               Generate row for each VALID accession that includes:
               [
                   "Registration Timestamp",
                   "96 Sample Plate",
                   "Well",
                   "Accession",
                   "Registered",
                   "Started RNA Extraction",
                   "PCR Barcode",
                   "qPCR Processing Complete",
                   "Processing Timestamp",
               }
    Parameters
    ----------
    :param cfg: Config instance
    :param google_creds: google Credentials instance
    """

    def __init__(self, cfg, google_creds):
        self.cfg = cfg
        self.drive_service = drive.get_service(google_creds)
        self.verbose_data = [VERBOSE_SHEET_HEADER]
        self.clin_lab_data = [CLIN_LAB_SHEET_HEADER]
        self.supervisor_plate_queue_data = [SUPERVISOR_PLATE_QUEUE_HEADER]

        self.gc = gutils.get_gspread_connection(google_creds)
        logger.info(msg="Initializing processing resources")
        self.processing_resources = ProcessingResources(self.drive_service, self.cfg)

    def compile_accessions_from_list(
        self, sample_barcodes: List[str], local_processing: bool
    ):
        """Compile accessions from list of sample barcodes"""
        for sample_barcode in sample_barcodes:
            try:
                accession_folder_entry = drive.find_file_by_search_terms(
                    self.drive_service,
                    self.processing_resources.accession_folder_id,
                    [sample_barcode, ".csv"],
                    drive.FindMode.MOST_RECENTLY_MODIFIED,
                )
            except NoMatchesError:
                # try for legacy
                try:
                    accession_folder_entry = drive.find_file_by_search_terms(
                        self.drive_service,
                        self.processing_resources.accession_folder_id,
                        [sample_barcode, ".xlsx"],
                        drive.FindMode.MOST_RECENTLY_MODIFIED,
                    )
                except NoMatchesError:
                    logger.error(
                        f"Could not find plate layout file for barcode: {sample_barcode}"
                    )
                    continue
            self.compile_accession_info_from_file(
                accession_folder_entry, local_processing
            )

    def save_local_results(self, run_path):
        """Save the results from accession tracking to two local files to the given run path"""
        run_path = pathlib.Path(run_path)
        accession_tracking_file = (
            run_path / f"{self.processing_resources.accessions_sheet}.csv"
        )
        with accession_tracking_file.open("w") as fh:
            for row in self.verbose_data:
                fh.write(",".join([str(e) for e in row]) + "\n")
        clin_lab_reporting_file = (
            run_path / f"{self.processing_resources.clin_lab_sheet}.csv"
        )
        with clin_lab_reporting_file.open("w") as fh:
            for row in self.clin_lab_data:
                fh.write(",".join([str(e) for e in row]) + "\n")
        supervisor_plate_queue_file = (
            run_path / f"{self.processing_resources.supervisor_plate_queue_sheet}.csv"
        )
        with supervisor_plate_queue_file.open("w") as fh:
            for row in self.supervisor_plate_queue_data:
                fh.write(",".join([str(e) for e in row]) + "\n")

    def write_marker_file(self, sample_barcode):
        """Writes a marker file for the given results"""
        marker_folder_id = drive.get_folder_id_of_path(
            self.drive_service, self.cfg.ACCESSSION_TRACKING_MARKERS_FOLDER
        )
        with drive.put_file(self.drive_service, marker_folder_id, sample_barcode):
            ...

    def save_gdrive_results(self):
        """Save accession tracking results to the google sheets defined in the cfg"""
        # Write result
        logger.info(msg=f"Updating {self.processing_resources.accessions_sheet} Sheet")
        self.updated_sheet_data(
            spreadsheet_name=self.processing_resources.accessions_sheet,
            source_data_sheet_id=self.cfg["DATA"].get("accession_tracking_sheet_id"),
            sheet_name="Verbose",
            barcode_column="96 Sample Plate",
            new_data=self.verbose_data,
        )
        logger.info(msg=f"Updating {self.processing_resources.clin_lab_sheet} Sheet")
        self.updated_sheet_data(
            spreadsheet_name=self.processing_resources.clin_lab_sheet,
            source_data_sheet_id=self.cfg["DATA"].get("clin_lab_reporting_sheet_id"),
            sheet_name="Clin Lab Reporting",
            barcode_column="96 Sample Plate",
            new_data=self.clin_lab_data,
        )
        logger.info(
            msg=f"Updating {self.processing_resources.supervisor_plate_queue_sheet} Sheet"
        )
        self.updated_sheet_data(
            spreadsheet_name=self.processing_resources.supervisor_plate_queue_sheet,
            source_data_sheet_id=self.cfg["DATA"].get(
                "supervisor_plate_queue_sheet_id"
            ),
            sheet_name="data",
            barcode_column="Sample plate number",
            new_data=self.supervisor_plate_queue_data,
        )

    def compile_accessions(
        self,
        updates_only=False,
        sample_barcodes: Optional[List[str]] = None,
        run_path: Optional[str] = None,
    ):
        """Compile all accession data from the Plate Layout Folder

        Parameters
        ----------
        :param updates_only: If true only process sample plate barcodes we haven't seen before
        :param sample_barcodes: optional specific barcodes to compile
        :param run_path: if defined save the results to this local destination, if None save to drive
        """
        logger.info(
            f"Compiling accession data:"
            f"updats_only: {updates_only} "
            f"sample_barcodes: {sample_barcodes} "
            f"run_path: {run_path}"
        )
        local_processing = True if run_path else False
        if not sample_barcodes:
            sample_barcodes = extract_all_barcodes_from_plate_layout_folder(
                self.drive_service, self.processing_resources.accession_folder_id
            )
            if updates_only:
                processed_sample_barcodes = get_already_tracked_samples(
                    self.drive_service, self.cfg
                )
                sample_barcodes = sample_barcodes - processed_sample_barcodes
        self.compile_accessions_from_list(
            sample_barcodes=sample_barcodes, local_processing=local_processing
        )
        if local_processing:
            self.save_local_results(run_path)
        else:
            self.save_gdrive_results()

    def compile_accession_info_from_file(self, accession_file, local_processing):
        """
        Generate accession tracking information for all accessions in the given sample barcode and
        append information.
        """
        name = accession_file.name
        binary_mode = False
        if name.endswith(".xlsx"):
            binary_mode = True
        with drive.get_file(
            self.drive_service, accession_file.id, binary=binary_mode
        ) as fh:
            plate_map_type = get_plate_map_type_from_name(name)

            try:
                well_to_accession = read_accession_data(plate_map_type, fh)
            except Exception as e:
                logger.error(
                    f"Could not extract accessions info from filename {name}, skipping, exception: {e}"
                )
                return

            timestamp = extract_timestamp_from_plate_map_filename(name, plate_map_type)
            sample_barcode = extract_barcode_from_plate_map_filename(
                name, plate_map_type
            )
            if not sample_barcode:
                logger.error(
                    f"Could not extract sample barcode from filename {name}, skipping"
                )
                return
            tracker = SampleTracker(
                timestamp=timestamp,
                sample_barcode=sample_barcode,
                drive_service=self.drive_service,
                processing_resources=self.processing_resources,
            )
            self.supervisor_plate_queue_data.append(
                tracker.format_row_entry_for_supervisor_plate_queue()
            )
            if plate_map_type != PlateMapType.LEGACY:
                for well, accession in well_to_accession.items():
                    if accession != "CONTROL" and accession != "EMPTY":
                        for entry in tracker.format_verbose_row_entries(
                            well, accession
                        ):
                            self.verbose_data.append(entry)
                        if re.match(VALID_ACCESSION, accession.rstrip()):
                            # only add valid accessions to the clin lab sheet
                            for entry in tracker.format_row_entries_clin_lab(
                                well, accession
                            ):
                                self.clin_lab_data.append(entry)
        if not local_processing and tracker.finished_processing:
            self.write_marker_file(sample_barcode=sample_barcode)

    def updated_sheet_data(
        self,
        spreadsheet_name,
        source_data_sheet_id,
        sheet_name,
        barcode_column,
        new_data,
    ):
        """
        Get the existing sheet data from prod drive and update with our new values

        Parameters
        ----------
        :param spreadsheet_name: The name of the google spreadsheet to update
        :param source_data_sheet_id: The ID of the prod sheet to get existing data from
        :param sheet_name: The name of the worksheet within the spreadsheet to update
        :param barcode_column: The name sample plate barcode column in the sheet
        :param new_data: The new data to update the sheet with
        """
        existing_data_df = CollectiveForm(
            self.drive_service, source_data_sheet_id, skip_header=False
        )[sheet_name]
        # create dataframe from processed values
        new_values_df = pd.DataFrame(new_data[1:], columns=new_data[0])
        values_to_remove = set(new_values_df[barcode_column].values)
        # remove all processed barcodes from existing data so we can replace
        existing_data_df = existing_data_df[
            ~existing_data_df[barcode_column].isin(values_to_remove)
        ]

        # now add new values
        existing_data_df = pd.concat(
            [new_values_df, existing_data_df], ignore_index=True
        )
        existing_data_df.fillna("", inplace=True)

        spread_sheet = self.gc.open(spreadsheet_name)
        spread_sheet.values_clear(range=f"{sheet_name}!A2")
        # update the sheet
        spread_sheet.values_update(
            f"{sheet_name}!A2",
            params={"valueInputOption": "RAW"},
            body={"values": existing_data_df.values.tolist()},
        )
