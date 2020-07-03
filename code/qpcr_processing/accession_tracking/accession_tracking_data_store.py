import csv
import logging
from typing import Dict, Tuple

from covidhub.collective_form import CollectiveForm
from covidhub.constants import PlateMapType
from covidhub.constants.qpcr_forms import (
    BravoRNAExtraction,
    BravoStart,
    FreezerCheckin,
    FridgeCheckin,
    SampleRegistration,
)
from covidhub.google import drive

logger = logging.getLogger(__name__)


class ProcessingResources:
    """Class that initializes the data needed for accession tracking"""

    def __init__(self, drive_service, cfg):
        self.completed_pcr_barcodes = get_completed_pcr_barcodes(drive_service, cfg)
        self.results_folder_id = drive.get_folder_id_of_path(
            drive_service, cfg.CSV_RESULTS_FOLDER_TRACKING
        )
        self.accession_folder_id = drive.get_folder_id_of_path(
            drive_service, cfg.PLATE_LAYOUT_FOLDER
        )
        self.accession_locations = get_accession_locations(drive_service, cfg)
        self.mark_as_processed_sample_barcodes = get_mark_as_processed_sample_barcodes(
            drive_service, cfg
        )
        self.accessions_sheet = cfg["DATA"].get("accession_tracking_sheet")
        self.clin_lab_sheet = cfg["DATA"].get("clin_lab_reporting_sheet")
        self.supervisor_plate_queue_sheet = cfg["DATA"].get(
            "supervisor_plate_queue_sheet"
        )
        form_responses = CollectiveForm(
            drive_service, cfg["DATA"].get("collection_form_spreadsheet_id")
        )
        self.registered_df = form_responses[SampleRegistration.SHEET_NAME]
        self.bravo_rna_df = form_responses[BravoRNAExtraction.SHEET_NAME]
        self.check_in_df = form_responses[FridgeCheckin.SHEET_NAME]
        self.starting_bravo_df = form_responses[BravoStart.SHEET_NAME]
        self.freezer_check_in_df = form_responses[FreezerCheckin.SHEET_NAME]


def extract_all_barcodes_from_plate_layout_folder(drive_service, accession_folder_id):
    """Return a set of all sample barcodes in the plate layout folder"""
    all_sample_barcodes = set()
    logger.info(msg="Grabbing contents from PlateLayout Folder")
    accession_folder_contents = get_accession_folder_contents(
        drive_service, accession_folder_id
    )
    for accession_folder_entry in accession_folder_contents:
        name = accession_folder_entry.name
        if name.endswith(".png") or name.endswith(".txt"):
            # there's some randos in there
            continue
        plate_map_type = PlateMapType.WELLLIT
        if "hamilton" in name:
            plate_map_type = PlateMapType.HAMILTON
        elif name.endswith(".xlsx"):
            plate_map_type = PlateMapType.LEGACY
        sample_barcode = extract_barcode_from_plate_map_filename(name, plate_map_type)
        if not sample_barcode:
            logger.error(f"could not extract barcode from filename: {name}")
            continue
        all_sample_barcodes.add(sample_barcode)
    return all_sample_barcodes


def get_mark_as_processed_sample_barcodes(drive_service, cfg):
    """Return list of sample barcodes that were never run and never going to be run from the
    "Do Not Process" Samples Spreadsheet"""
    collective_form = CollectiveForm(
        drive_service, cfg["DATA"]["do_not_process_spreadsheet_id"], skip_header=False
    )
    return list(collective_form["barcodes"]["sample_barcodes"].values)


def extract_barcode_from_plate_map_filename(filename, plate_map_type: PlateMapType):
    if plate_map_type == PlateMapType.WELLLIT:
        return filename.split("_")[1]
    elif plate_map_type == PlateMapType.HAMILTON:
        return filename.split("_")[1]
    elif plate_map_type == PlateMapType.LEGACY:
        if filename.startswith("96sample"):
            # filename in format '96sample_plate_accessions_SP000217 - Vida Ahyong.xlsx'
            return filename.split("-")[0].split("_")[-1].rstrip()
        elif filename.startswith("SP"):
            # filename format is "SP000226 - Vida Ahyong.xlsx"
            return filename.split("-")[0].rstrip()
    return None


def extract_timestamp_from_plate_map_filename(filename, plate_map_type: PlateMapType):
    if plate_map_type == PlateMapType.WELLLIT:
        return filename.split("_")[0]
    elif plate_map_type == PlateMapType.HAMILTON:
        # Note, hamilton appears to be MMDDYYYY-HHMMSS, as opposed to
        # WellLit which is YYYYMMDD-HHMMSS
        return filename.split("_")[0]
    elif plate_map_type == PlateMapType.LEGACY:
        return ""


def get_completed_pcr_barcodes(drive_service, cfg):
    """Return a list of processed qPCR barcodes by checking our marker file folder"""
    marker_folder_id = drive.get_folder_id_of_path(
        drive_service, cfg.PCR_MARKERS_FOLDER_TRACKING
    )

    marker_folder_contents = drive.get_contents_by_folder_id(
        drive_service, marker_folder_id, only_files=True
    )

    completed_barcodes = set(
        marker_folder_entry.name for marker_folder_entry in marker_folder_contents
    )
    return completed_barcodes


def get_already_tracked_samples(drive_service, cfg):
    """Return a list of processed qPCR barcodes by checking our marker file folder"""
    marker_folder_id = drive.get_folder_id_of_path(
        drive_service, cfg.ACCESSSION_TRACKING_MARKERS_FOLDER
    )

    marker_folder_contents = drive.get_contents_by_folder_id(
        drive_service, marker_folder_id, only_files=True
    )

    completed_barcodes = set(
        marker_folder_entry.name for marker_folder_entry in marker_folder_contents
    )
    return completed_barcodes


def get_accession_folder_contents(drive_service, accession_folder_id):
    """Return the contents of the WellLit accessions folder (also includes Hamilton files)"""
    return drive.get_contents_by_folder_id(
        drive_service, accession_folder_id, only_files=True
    )


def get_accession_locations(drive_service, cfg) -> Dict[str, Tuple[str, str]]:
    """return a mapping between accession ID's and their origin location"""
    accession_locations = {}
    accession_location_folder_id = drive.get_folder_id_of_path(
        drive_service, cfg.ACCESSION_LOCATIONS_FOLDER
    )
    accession_location_files = drive.get_contents_by_folder_id(
        drive_service, accession_location_folder_id, only_files=True
    )
    for accession_location_file in accession_location_files:
        with drive.get_file(drive_service, accession_location_file.id) as fh:
            accession_location_reader = csv.reader(fh, delimiter=",")
            for row in accession_location_reader:
                if row[0] == "Accession":
                    # header row
                    continue
                submitter_id = ""
                if len(row) == 3:
                    accession, location, submitter_id = row
                else:
                    accession, location = row
                accession_locations[accession] = location, submitter_id
    return accession_locations
