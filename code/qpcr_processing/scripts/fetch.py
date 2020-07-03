import logging
import pathlib
from collections import defaultdict

import covidhub.google.utils as gutils
from covidhub.config import Config
from covidhub.google import drive
from covidhub.logging import create_logger
from qpcr_processing.run_files import RunFiles

logger = logging.getLogger(__name__)


def fetch_barcodes(args, cfg):
    google_credentials = gutils.get_secrets_manager_credentials(args.secret_id)
    drive_service = drive.get_service(google_credentials)

    # qpcr logs folder
    logs_folder_id = drive.get_folder_id_of_path(drive_service, cfg.PCR_LOGS_FOLDER)
    logs_folder_contents = drive.get_contents_by_folder_id(
        drive_service, logs_folder_id, only_files=True
    )

    barcodes_to_fetch = defaultdict(RunFiles)
    for entry in logs_folder_contents:
        m = RunFiles.get_qpcr_file_type(entry.name)
        if m is None:
            continue
        elif m[RunFiles.BARCODE] in args.barcodes:
            barcodes_to_fetch[m[RunFiles.BARCODE]].add_file(m, entry)

    for barcode, barcode_files in barcodes_to_fetch.items():
        # all files must be present, at least one quant_amp file
        if not barcode_files.all_files:
            logger.warning(msg=f"Missing files for {barcode}!")
            continue

        logger.info(msg=f"Found sample to fetch: {barcode}")

        # read in the run information and quant cq
        run_info = barcode_files.run_info
        logger.info(msg=f"    Downloading: {run_info.name}")
        with drive.get_file(drive_service, run_info.id, binary=False) as fh:
            with (args.output_dir / run_info.name).open("w") as out:
                out.write(fh.read())

        quant_cq = barcode_files.quant_cq
        logger.info(msg=f"    Downloading: {quant_cq.name}")
        with drive.get_file(drive_service, quant_cq.id, binary=False) as fh:
            with (args.output_dir / quant_cq.name).open("w") as out:
                out.write(fh.read())

        for quant_amp in barcode_files.quant_amp.values():
            logger.info(msg=f"    Downloading: {quant_amp.name}")
            with drive.get_file(drive_service, quant_amp.id, binary=False) as fh:
                with (args.output_dir / quant_amp.name).open("w") as out:
                    out.write(fh.read())


def main():
    import argparse

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("barcodes", nargs="+")
    parser.add_argument("--output-dir", type=pathlib.Path, default=pathlib.Path("."))
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--secret-id", default="covid-19/google_creds")

    args = parser.parse_args()

    cfg = Config()
    create_logger(cfg, debug=args.debug)

    fetch_barcodes(args, cfg)


if __name__ == "__main__":
    main()
