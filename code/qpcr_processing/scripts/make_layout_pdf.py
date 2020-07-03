import argparse
import json
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, BinaryIO, Dict

import dateutil
from reportlab.graphics.barcode.code128 import Code128
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Table, TableStyle

import covidhub.google.utils as gutils
import qpcr_processing.accession as accession
from covidhub.collective_form import clean_single_row, CollectiveForm
from covidhub.config import Config
from covidhub.constants import COLS_96, ROWS_96, VALID_ACCESSION
from covidhub.constants.qpcr_forms import SampleMetadata
from covidhub.error import BadDriveURL, MetadataNotFoundError, MultipleRowsError
from covidhub.google import drive
from covidhub.logging import create_logger

logger = logging.getLogger(__name__)


# add this key to entry_data to indicate we're running locally
LOCAL_RUN = "local_run"


def format_time(cfg: Config, timestamp: str) -> str:
    """Format a timestamp string into the preferred YYYY-MM-DD HH:MM TZ format,
    using the configured timezone."""
    timezone = dateutil.tz.gettz(cfg["GENERAL"].get("timezone", "America/Los Angeles"))

    # parse UTC timestamp and convert to timezone
    dt = dateutil.parser.parse(timestamp).astimezone(timezone)

    # format as desired
    return dt.strftime("%Y-%m-%d %H:%M %Z")


class _PDF:
    MARGIN = 0.25 * inch

    BARCODE_HEIGHT = 0.3 * inch
    BARCODE_WIDTH = 0.0075 * inch  # the width of the skinniest individual bar


def format_pdf(
    sample_barcode: str,
    accession_data: Dict[str, str],
    researcher: str,
    timestamp: str,
    output_file_handle: BinaryIO,
):
    """Create a 96 well plate map with barcodes, for paper trail. This function
    does all of the fun ReportLab formatting and layout.

    Parameters
    ----------
    sample_barcode: str
        Sample plate barcode for the title
    accession_data: Dict[str, str]
        Dictionary of well to accession data, just as in the standard pipeline
    researcher: str
        Name of the researcher who submitted this layout
    timestamp: str
        Pre-formatted timestamp of the submission
    output_file_handle: BinaryIO
        file handle for writing the PDF
    """
    styles = getSampleStyleSheet()
    doc = BaseDocTemplate(
        output_file_handle,
        pagesize=landscape(letter),
        rightMargin=_PDF.MARGIN,
        leftMargin=_PDF.MARGIN,
        topMargin=_PDF.MARGIN,
        bottomMargin=_PDF.MARGIN,
    )

    landscape_frame = Frame(0, 0, letter[1], letter[0], id="landscape_frame")
    doc.addPageTemplates(
        [
            PageTemplate(
                id="landscape", frames=landscape_frame, pagesize=landscape(letter)
            ),
        ]
    )

    # this is the style for the overall table. Black gridlines,
    # and no padding around the values in the cells
    table_style = TableStyle(
        [
            ("FONT", (0, 0), (-1, 0), styles["Heading1"].fontName),  # bold header
            ("FONTSIZE", (0, 0), (-1, 0), 16),
            ("SPAN", (0, 0), (4, 0)),
            ("SPAN", (5, 0), (8, 0)),
            ("SPAN", (9, 0), (-1, 0)),
            ("BOX", (1, 2), (-1, -1), 0.5, colors.black),
            ("INNERGRID", (1, 2), (-1, -1), 0.5, colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]
    )

    plate_map_dict = defaultdict(dict)

    # the style for a mini-table inside a cell.
    # no grid, and a little padding
    cell_style = TableStyle(
        [
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ]
    )

    for row in ROWS_96:
        for col in COLS_96:
            well_id = f"{row}{col}"
            if well_id not in accession_data:
                continue

            well_data = accession_data[well_id]
            if not re.match(VALID_ACCESSION, well_data):
                continue

            cell_content = Table(
                [
                    [
                        Code128(
                            well_data,
                            barHeight=_PDF.BARCODE_HEIGHT,
                            barWidth=_PDF.BARCODE_WIDTH,
                        )
                    ],
                    [well_data],
                ]
            )

            cell_content.setStyle(cell_style)

            plate_map_dict[row][col] = cell_content

    # Create plate map column labels
    plate_map_data = [
        [
            f"Researcher: {researcher}",
            "",
            "",
            "",
            "",
            sample_barcode,
            "",
            "",
            "",
            f"At: {timestamp}",
            "",
            "",
            "",
        ],
        ["", *(col for col in COLS_96)],
    ]
    plate_map_data.extend(
        [row, *(plate_map_dict[row].get(col, "") for col in COLS_96)] for row in ROWS_96
    )

    # this table will fill an entire landscape page
    plate_map = Table(
        plate_map_data,
        colWidths=[0.2 * inch] + [0.85 * inch] * 12,
        rowHeights=[0.5 * inch, 0.2 * inch] + [0.9 * inch] * 8,
        style=table_style,
    )

    doc.build([plate_map])


def create_layout_pdf(cfg: Config, entry_data: Dict[str, str]):
    """Main function to read a layout file and write the resulting plate layout map.

    Parameters
    ----------
    cfg: Config
        configuration information
    entry_data: Dict[str, str]
        dictionary containing the response that was submitted to Sample Plate Metada.
        The required keys are: the researcher, timestamp, sample plate barcode, and a
        link to the sample plate map in Google Drive. Optionally, the "local_run" key
        is used as a flag to indicate the script is being run from the command line
        rather than on AWS.
    """
    sample_barcode = entry_data[SampleMetadata.SAMPLE_PLATE_BARCODE]
    output_filename = f"{sample_barcode}.pdf"

    if LOCAL_RUN in entry_data:
        output_path, drive_service = entry_data[LOCAL_RUN]
        output_file_object = (output_path / output_filename).open("wb")
    else:
        logger.debug("getting gdrive credentials")
        google_creds = gutils.get_secrets_manager_credentials()
        drive_service = drive.get_service(google_creds)

        processed_layout_folder_id = drive.get_folder_id_of_path(
            drive_service, cfg.LAYOUT_PDF_FOLDER
        )

        output_file_object = drive.put_file(
            drive_service, processed_layout_folder_id, output_filename, binary=True,
        )

    try:
        plate_map_file = drive.get_layout_file_from_url(
            drive_service, entry_data[SampleMetadata.SAMPLE_PLATE_MAP]
        )
    except KeyError:
        raise BadDriveURL(
            f"Bad URL in {SampleMetadata.SHEET_NAME} for {sample_barcode}"
        )

    plate_map_type = accession.get_plate_map_type_from_name(plate_map_file.name)

    with plate_map_file.open() as fh:
        accession_data = accession.read_accession_data(plate_map_type, fh)

    logger.info(f"Writing layout map to {output_filename}")
    with output_file_object as output_fh:
        format_pdf(
            entry_data[SampleMetadata.SAMPLE_PLATE_BARCODE],
            accession_data,
            entry_data[SampleMetadata.RESEARCHER_NAME],
            format_time(cfg, entry_data[SampleMetadata.TIMESTAMP]),
            output_fh,
        )


def lambda_handler(entry: Dict[str, Any], context):
    """AWS Lambda entry point.

    Parameters
    ----------
    entry : Dict
        Dictionary passed to the entry point by AWS. The value of 'body' will be loaded
        as json to form the entry_data dictionary.
    context :
        AWS Lambda context object. Not used here.
    """
    cfg = Config()
    create_logger(cfg)

    entry_data = json.loads(entry["body"])
    logger.info(f"got entry: {entry_data}")

    try:
        create_layout_pdf(cfg=cfg, entry_data=entry_data)
    except Exception as err:
        logger.critical(
            f"Error in [{cfg.aws_env}]: {err}", extra={"notify_slack": True}
        )
        logger.exception("Details:")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("barcodes", nargs="+")
    parser.add_argument("--output-dir", type=Path, default=Path("."))

    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--secret-id", default="covid-19/google_creds")

    args = parser.parse_args()

    cfg = Config()
    create_logger(cfg, debug=args.debug)

    google_creds = gutils.get_secrets_manager_credentials(args.secret_id)
    drive_service = drive.get_service(google_creds)

    logger.debug("Downloading collective form")
    collective_form = CollectiveForm(
        drive_service, cfg["DATA"]["collection_form_spreadsheet_id"]
    )
    sample_plate_metadata = collective_form[SampleMetadata.SHEET_NAME]

    for barcode in args.barcodes:
        try:
            metadata_row = clean_single_row(
                sample_plate_metadata, SampleMetadata.SAMPLE_PLATE_BARCODE, barcode
            )
        except MetadataNotFoundError:
            logger.error(f"0 results for {barcode}, skipping")
            continue
        except MultipleRowsError as ex:
            logger.error(f"{ex.match_count} results for {barcode}, skipping")
            continue
        metadata_row[SampleMetadata.TIMESTAMP] = str(
            metadata_row[SampleMetadata.TIMESTAMP]
        )
        metadata_row[LOCAL_RUN] = (args.output_dir, drive_service)

        logger.debug(f"Making layout PDF for {barcode}")
        create_layout_pdf(cfg=cfg, entry_data=metadata_row)
