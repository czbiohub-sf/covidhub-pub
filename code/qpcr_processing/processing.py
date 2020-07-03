import csv
import io
import logging
import pathlib
from collections import defaultdict
from typing import Dict

import pandas as pd
from google.oauth2 import service_account

import covidhub.google.utils as gutils
import qpcr_processing.accession as accession
from covidhub.collective_form import CollectiveForm
from covidhub.config import Config, get_git_info
from covidhub.constants.qpcr_forms import SampleMetadata, SampleRerun
from covidhub.google import drive, mail
from covidhub.logging import create_logger
from qpcr_processing.control_wells import (
    get_control_wells_from_type,
    update_accession_data_with_controls,
)
from qpcr_processing.make_final_results_pdf import create_final_pdf
from qpcr_processing.metadata import BravoMetadata, qPCRData
from qpcr_processing.plate_utils import map_384_to_96
from qpcr_processing.processing_results import ProcessingResults
from qpcr_processing.protocol import get_protocol, Protocol
from qpcr_processing.run_files import RunFiles
from qpcr_processing.well_results import WellResults

logger = logging.getLogger(__name__)


def _format_email_subject(sample_barcode, qpcr_barcode):
    return f"[CLIAHUB Report] Sample plate {sample_barcode}-{qpcr_barcode} Results"


def _format_email_body(sample_barcode, results_file_id):
    body = f"""\
Hello,

The results for sample plate {sample_barcode} are complete.

The report is available here:
{drive.GDRIVE_ID_FORMAT_STRING.format(results_file_id)}
Thank you,

CLIAHUB Bot
"""
    return body


def process_barcode(
    cfg: Config,
    barcode: str,
    barcode_files: RunFiles,
    bravo_metadata: BravoMetadata,
    protocol: Protocol,
    control_wells: Dict[str, str],
    accession_data: Dict[str, str],
):
    logger.info(msg=f"Processing barcode: {barcode}")

    # read in the run information and quant cq
    with barcode_files.run_info.open("r") as fh:
        run_info = dict(csv.reader(fh))

    with barcode_files.quant_cq.open("r") as fh:
        quant_cq_results = pd.read_csv(fh, sep=",")

    quant_amp_data = {}
    for fluor, quant_amp_file in barcode_files.quant_amp.items():
        with quant_amp_file.open("r") as fh:
            quant_amp_data[fluor] = pd.read_csv(fh, sep=",")

    qPCR_data = qPCRData(protocol, barcode, run_info, quant_cq_results)

    results = local_processing(qPCR_data.data, control_wells, protocol)

    # add accession data from plate layout
    if accession_data:
        logger.info(msg=f"Adding accession info for: {barcode}")
        results = accession.add_accession_barcodes_to_results(results, accession_data)
    else:
        logger.warning(msg="Accession info missing")

    processing_results = ProcessingResults.from_results_data(
        cfg=cfg,
        well_to_results_mapping=results,
        protocol=protocol,
        bravo_metadata=bravo_metadata,
        run_ended=qPCR_data.run_ended,
        quant_amp_data=quant_amp_data,
    )

    return processing_results


def processing(cfg: Config, google_credentials: service_account.Credentials):
    git_info = get_git_info()
    drive_service = drive.get_service(google_credentials)
    logger.info(msg=f"Starting processing loop with code version: {git_info}")

    # qpcr logs folder
    logs_folder_id = drive.get_folder_id_of_path(drive_service, cfg.PCR_LOGS_FOLDER)

    # markers folder
    markers_folder_id = drive.get_folder_id_of_path(
        drive_service, cfg.PCR_MARKERS_FOLDER
    )

    # csv results folder
    csv_results_folder_id = drive.get_folder_id_of_path(
        drive_service, cfg.CSV_RESULTS_FOLDER
    )

    # CB rad results folder
    cb_report_folder_id = drive.get_folder_id_of_path(
        drive_service, cfg.CHINA_BASIN_CSV_REPORTS_FOLDER
    )

    # final reports folder
    final_results_folder_id = drive.get_folder_id_of_path(
        drive_service, cfg.FINAL_REPORTS_FOLDER
    )

    # get the collection spreadsheet
    collective_form = CollectiveForm(
        drive_service, cfg["DATA"]["collection_form_spreadsheet_id"]
    )

    logs_folder_contents = drive.get_contents_by_folder_id(
        drive_service, logs_folder_id, only_files=True
    )
    marker_folder_contents = drive.get_contents_by_folder_id(
        drive_service, markers_folder_id, only_files=True
    )
    plate_layout_folder_id = drive.get_folder_id_of_path(
        drive_service, cfg.PLATE_LAYOUT_FOLDER
    )
    completed_barcodes = set(
        marker_folder_entry.name for marker_folder_entry in marker_folder_contents
    )

    sample_metadata_form = collective_form[SampleMetadata.SHEET_NAME]
    rerun_form = collective_form[SampleRerun.SHEET_NAME]

    # group log file entries by barcode
    logger.info(msg="Checking for samples to process")

    barcodes_to_process = defaultdict(RunFiles)
    for entry in logs_folder_contents:
        m = RunFiles.get_qpcr_file_type(entry.name)
        if m is None or m[RunFiles.BARCODE] in completed_barcodes:
            continue
        else:
            barcodes_to_process[m[RunFiles.BARCODE]].add_file(m, entry)

    for barcode, barcode_files in barcodes_to_process.items():
        # all files must be present, at least one quant_amp file
        if not barcode_files.all_files:
            message = f"Missing files for: {barcode}. Skipping for now"
            logger.critical(msg=message, extra={"notify_slack": True})
            continue

        try:
            logger.info(msg=f"Found sample to process, barcode: {barcode}")

            logger.info(msg=f"Getting metadata and data for: {barcode}")
            bravo_metadata = BravoMetadata.load_from_spreadsheet(
                barcode, collective_form,
            )
            if bravo_metadata.sop_protocol is None:
                message = f"Skipping sample plate: {barcode}, no protocol"
                logger.critical(msg=message, extra={"notify_slack": True})
                continue

            protocol = get_protocol(bravo_metadata.sop_protocol)

            if not set(barcode_files.quant_amp).issuperset(protocol.mapping):
                missing = map(str, set(protocol.mapping) - set(barcode_files.quant_amp))
                message = f"Missing quant amp files for {barcode}: {', '.join(missing)}"
                logger.critical(msg=message, extra={"notify_slack": True})
                continue

            # process well data and check controls, return results
            logger.info(msg=f"Processing well data and controls for: {barcode}")
            accession_data = accession.get_accession_data_with_rerun(
                drive_service,
                plate_layout_folder_id,
                sample_metadata_form,
                rerun_form,
                bravo_metadata.sample_barcode,
            )

            control_wells = get_control_wells_from_type(
                controls_type=bravo_metadata.controls_type,
                accession_data=accession_data,
            )
            update_accession_data_with_controls(control_wells, accession_data, barcode)

            processing_results = process_barcode(
                cfg,
                barcode,
                barcode_files,
                bravo_metadata,
                protocol,
                control_wells,
                accession_data,
            )

            with drive.put_file(
                drive_service,
                csv_results_folder_id,
                processing_results.results_filename,
            ) as fh:
                processing_results.write_results(fh)

            china_basin_result_file = drive.put_file(
                drive_service,
                cb_report_folder_id,
                processing_results.cb_report_filename,
            )
            with china_basin_result_file as fh:
                processing_results.write_cb_report(fh)

            # create pdf report
            logger.info(msg=f"Generating and uploading results PDF for: {barcode}")
            final_pdf = io.BytesIO()
            create_final_pdf(processing_results, final_pdf)
            pdf_results_file = drive.put_file(
                drive_service,
                final_results_folder_id,
                processing_results.final_pdf_filename,
            )
            with pdf_results_file as out_fh:
                out_fh.write(final_pdf.getvalue())

            logger.info(msg=f"Sending email report: {barcode}")
            mail.send_email(
                google_credentials,
                sender=cfg["EMAIL"].get("sender"),
                recipients=cfg["EMAIL"].get("recipients"),
                subject=_format_email_subject(
                    sample_barcode=bravo_metadata.sample_barcode, qpcr_barcode=barcode,
                ),
                body=_format_email_body(
                    sample_barcode=bravo_metadata.sample_barcode,
                    results_file_id=china_basin_result_file.id,
                ),
                attachments={processing_results.final_pdf_filename: final_pdf},
            )

            message = (
                f"Processed sample plate: {bravo_metadata.sample_barcode}-{barcode}"
                f" using rev {git_info}"
            )
            logger.critical(msg=message, extra={"notify_slack": True})
            # write a marker so we don't process this file again.
            processing_results.write_marker_file(drive_service, markers_folder_id)

        except Exception as err:
            logger.critical(
                f"Error in [{cfg.aws_env}]: {err}", extra={"notify_slack": True}
            )
            logger.exception("Details:")


def local_processing(data, control_wells, protocol: Protocol):
    logger.info(msg=f"Starting call logic, using protocol: {protocol.name}")
    results = {}

    for well, values in map_384_to_96(data, protocol.mapping).items():
        if well in control_wells:
            control_type = control_wells[well]
            call = protocol.check_control(values, control_type)
        else:
            control_type = None
            call = protocol.call_well(values)

        results[well] = WellResults(
            call=call, gene_cts=values, control_type=control_type
        )

    return results


def parse_qpcr_csv(args):
    cfg = Config()
    create_logger(cfg, debug=args.debug)

    logger.info(msg=f"Started local processing in: {args.qpcr_run_path}")

    if args.use_gdrive and not args.barcodes:
        raise ValueError("You must specify barcodes to process from Google Drive")

    run_path = pathlib.Path(args.qpcr_run_path)

    google_credentials = gutils.get_secrets_manager_credentials(args.secret_id)

    drive_service = drive.get_service(google_credentials)
    collective_form = CollectiveForm(
        drive_service, cfg["DATA"]["collection_form_spreadsheet_id"]
    )

    sample_metadata_form = collective_form[SampleMetadata.SHEET_NAME]
    rerun_form = collective_form[SampleRerun.SHEET_NAME]

    if args.use_gdrive:
        logs_folder_id = drive.get_folder_id_of_path(drive_service, cfg.PCR_LOGS_FOLDER)
        logs_folder_contents = [
            drive_file
            for drive_file in drive.get_contents_by_folder_id(
                drive_service, logs_folder_id, only_files=True
            )
        ]

        plate_layout_folder_id = drive.get_folder_id_of_path(
            drive_service, cfg.PLATE_LAYOUT_FOLDER
        )
    else:
        logs_folder_contents = run_path.glob("*.csv")

    barcodes_to_process = defaultdict(RunFiles)
    for run_file in logs_folder_contents:
        m = RunFiles.get_qpcr_file_type(run_file.name)
        if m is None:
            continue
        elif args.barcodes and m[RunFiles.BARCODE] not in args.barcodes:
            continue
        else:
            barcodes_to_process[m[RunFiles.BARCODE]].add_file(m, run_file)

    for barcode, barcode_files in barcodes_to_process.items():
        # all files must be present, at least one quant_amp file
        if not barcode_files.all_files:
            message = f"Missing files for: {barcode}. Skipping for now"
            logger.info(msg=message)
            continue

        logger.info(msg=f"Found sample to process, barcode: {barcode}")

        logger.info(msg=f"Getting metadata and data for: {barcode}")
        bravo_metadata = BravoMetadata.load_from_spreadsheet(barcode, collective_form)
        if args.protocol is not None:
            # user specified the protocol
            protocol = get_protocol(args.protocol)
        else:
            protocol = get_protocol(bravo_metadata.sop_protocol)

        if not set(barcode_files.quant_amp).issuperset(protocol.mapping):
            missing = map(str, set(protocol.mapping) - set(barcode_files.quant_amp))
            message = f"Missing quant amp files for {barcode}: {', '.join(missing)}"
            logger.critical(msg=message)
            continue

        if args.plate_map_file is not None:
            plate_map_type = accession.get_plate_map_type_from_name(
                args.plate_map_file.name
            )
            accession_data = accession.read_accession_data(
                plate_map_type, args.plate_map_file
            )
        elif args.use_gdrive:
            accession_data = accession.get_accession_data_with_rerun(
                drive_service,
                plate_layout_folder_id,
                sample_metadata_form,
                rerun_form,
                bravo_metadata.sample_barcode,
            )
        else:
            raise ValueError("You must provide a plate map file or use Google Drive")

        control_wells = get_control_wells_from_type(
            controls_type=bravo_metadata.controls_type, accession_data=accession_data,
        )
        # check for valid accessions
        update_accession_data_with_controls(control_wells, accession_data, barcode)

        # process well data and check controls, return results
        logger.info(msg=f"Processing well data and controls for: {barcode}")

        processing_results = process_barcode(
            cfg,
            barcode,
            barcode_files,
            bravo_metadata,
            protocol,
            control_wells,
            accession_data,
        )

        with (run_path / processing_results.results_filename).open("w") as fh:
            processing_results.write_results(fh)

        with (run_path / processing_results.cb_report_filename).open("w") as fh:
            processing_results.write_cb_report(fh)

        # create pdf report
        logger.info(msg=f"Generating results PDF for: {barcode}")
        final_pdf_filename = run_path / processing_results.final_pdf_filename
        with open(final_pdf_filename, "wb") as output_file:
            create_final_pdf(processing_results, output_file)


def lambda_handler(event, context):
    cfg = Config()
    create_logger(cfg)

    try:
        google_credentials = gutils.get_secrets_manager_credentials()
        processing(cfg, google_credentials)
    except Exception:
        logger.critical(f"Error in [{cfg.aws_env}]", exc_info=True)
        raise


def gdrive_processing(args):
    cfg = Config()
    create_logger(cfg, debug=args.debug)

    google_credentials = gutils.get_secrets_manager_credentials(args.secret_id)

    processing(cfg, google_credentials)
