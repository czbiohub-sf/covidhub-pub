import csv
import logging
import re
from typing import BinaryIO, Dict, IO, TextIO

import numpy as np
import pandas as pd
from googleapiclient.errors import HttpError

from covidhub.collective_form import clean_single_row, CollectiveForm
from covidhub.constants import (
    HAMILTON_ACCESSION_COLUMN,
    HAMILTON_COLUMN_NAMES,
    HAMILTON_PREFIX_FOR_EMPTY_WELLS,
    HAMILTON_WELL_COLUMN,
    MAP_96_TO_384_NO_PAD,
    PlateMapType,
    ROWS_96,
    WELLLIT_NAMES_FOR_EMPTY_WELLS,
)
from covidhub.constants.qpcr_forms import SampleMetadata, SampleRerun
from covidhub.error import BadDriveURL, InvalidWellID, MetadataNotFoundError
from covidhub.google.drive import (
    DriveService,
    find_file_by_search_terms,
    get_layout_file_from_url,
)

logger = logging.getLogger(__name__)


AccessionData = Dict[str, str]  # type alias for function annotations


def _validate_accession_data(accession_data: AccessionData):
    if not set(accession_data).issubset(MAP_96_TO_384_NO_PAD):
        invalid_wells = ", ".join(set(accession_data) - set(MAP_96_TO_384_NO_PAD))
        raise InvalidWellID(f"Invalid well ID(s): {invalid_wells}")


def process_hamilton(fh: TextIO) -> AccessionData:
    well_to_accession = {}

    accession_reader = csv.DictReader(fh, delimiter=",")

    if accession_reader.fieldnames != HAMILTON_COLUMN_NAMES:
        msg = (
            f"Error parsing Hamilton plate map {fh.name}. File contains "
            f"unexpected column names in order {accession_reader.fieldnames} "
            f"instead of expected order {HAMILTON_COLUMN_NAMES}."
        )
        logger.error(msg)
        raise ValueError(msg)

    for row in accession_reader:
        well = row[HAMILTON_WELL_COLUMN]
        accession_barcode = row[HAMILTON_ACCESSION_COLUMN]

        if accession_barcode.startswith(HAMILTON_PREFIX_FOR_EMPTY_WELLS):
            continue
        well_to_accession[well] = accession_barcode

    _validate_accession_data(well_to_accession)

    return well_to_accession


def process_welllit(fh: TextIO) -> AccessionData:
    well_to_accession = {}

    accession_reader = csv.reader(fh, delimiter=",")

    for row in accession_reader:
        # Metadata start with "%"
        if row[0].startswith("%") or row[0].startswith("\ufeff"):
            continue

        timestamp, accession_barcode, well = row
        if accession_barcode in WELLLIT_NAMES_FOR_EMPTY_WELLS:
            continue
        well_to_accession[well] = accession_barcode

    _validate_accession_data(well_to_accession)

    return well_to_accession


def parse_legacy_accession_data(fh: BinaryIO) -> AccessionData:
    accession_data = {}

    df = pd.read_excel(fh, header=None)

    for i, row in df.iterrows():
        if row[0] in ROWS_96:
            # Get each row from the pandas data frame if they are one of the
            # well rows (ninety_six_rows) and get all of the accession barcodes
            # flattened into a list.
            for j, value in enumerate(df.iloc[i][1:].replace(np.nan, "")):
                accession_data[f"{row[0]}{j+1}"] = value

    # should never fail, by construction
    _validate_accession_data(accession_data)

    return accession_data


def add_accession_barcodes_to_results(results, accession_data):
    for well_id, well_result in results.items():
        well_result.accession = accession_data.get(well_id, "")

    return results


def get_plate_map_type_from_name(plate_map_name: str) -> PlateMapType:
    if re.search(r"\.xlsx?$", plate_map_name.lower()):
        # xls/x files are assumed to be the legacy 8x12 format
        return PlateMapType.LEGACY
    elif "hamilton" in plate_map_name.lower():
        return PlateMapType.HAMILTON
    else:
        # assume well-lit file if we can't figure it out
        return PlateMapType.WELLLIT


def read_accession_data(
    plate_map_type: PlateMapType, plate_map_file: IO
) -> AccessionData:
    logger.info(
        msg=f"Getting accession data from {plate_map_type} file: {plate_map_file.name}"
    )

    if plate_map_type == PlateMapType.WELLLIT:
        return process_welllit(plate_map_file)
    elif plate_map_type == PlateMapType.HAMILTON:
        return process_hamilton(plate_map_file)
    elif plate_map_type == PlateMapType.LEGACY:
        return parse_legacy_accession_data(plate_map_file)
    else:
        raise ValueError(f"Unknown layout type {plate_map_type}")


def get_accession_data(
    service: DriveService,
    folder_id: str,
    sample_metadata_form: CollectiveForm,
    sample_barcode: str,
) -> AccessionData:
    metadata_row = sample_metadata_form[
        sample_metadata_form[SampleMetadata.SAMPLE_PLATE_BARCODE] == sample_barcode
    ]

    plate_map_file = None
    try:
        metadata_row = clean_single_row(
            metadata_row, SampleMetadata.SAMPLE_PLATE_BARCODE, sample_barcode, -1
        )
    except MetadataNotFoundError:
        logger.exception(f"No metadata found for {sample_barcode}")
    else:
        try:
            plate_map_file = get_layout_file_from_url(
                service, metadata_row[SampleMetadata.SAMPLE_PLATE_MAP]
            )
        except HttpError:
            logger.exception(f"Dead link in {SampleMetadata.SHEET_NAME}")
        except KeyError:
            raise BadDriveURL(
                f"Bad link in {SampleMetadata.SHEET_NAME} for {sample_barcode}"
            )

    if plate_map_file is None:
        logger.error(
            f"No results found in {SampleMetadata.SHEET_NAME}, "
            f"searching plate layout folder for {sample_barcode}"
        )
        plate_map_file = find_file_by_search_terms(service, folder_id, [sample_barcode])

    plate_map_type = get_plate_map_type_from_name(plate_map_file.name)

    with plate_map_file.open() as fh:
        accession_data = read_accession_data(plate_map_type, fh)

    return accession_data


def get_accession_data_with_rerun(
    service: DriveService,
    plate_layout_folder_id: str,
    sample_metadata_form: pd.DataFrame,
    rerun_form: pd.DataFrame,
    sample_barcode: str,
) -> AccessionData:
    # get the accession data for the given barcode
    accession_data = get_accession_data(
        service, plate_layout_folder_id, sample_metadata_form, sample_barcode
    )

    # check the rerun form in case this sample is being rerun
    rerun_rows = rerun_form.loc[
        rerun_form[SampleRerun.NEW_SAMPLE_PLATE_BARCODE] == sample_barcode
    ]

    # if any rows are found, update the accession data
    for _, row in rerun_rows.iterrows():
        sample_accession = row[SampleRerun.SAMPLE_ACCESSION]
        original_sample_barcode = row[SampleRerun.ORIGINAL_SAMPLE_PLATE_BARCODE]
        original_well = row[SampleRerun.ORIGINAL_WELL]
        new_sample_well = row[SampleRerun.NEW_WELL]

        prev_accession_data = get_accession_data(
            service,
            plate_layout_folder_id,
            sample_metadata_form,
            original_sample_barcode,
        )
        prev_accession_barcode = prev_accession_data[original_well]

        if sample_accession and (sample_accession != prev_accession_barcode):
            raise RuntimeError(
                f"User provided sample accession: {sample_accession}"
                " but it didn't match the previous run of:"
                f" {prev_accession_barcode}."
            )

        accession_data[new_sample_well] = prev_accession_barcode

    return accession_data
