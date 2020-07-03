import sys
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser, FileType

from qpcr_processing.accession_tracking.accession_tracking import compile_accessions_cli
from qpcr_processing.processing import gdrive_processing, parse_qpcr_csv


def main():
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--secret-id", default="covid-19/google_creds")

    subparsers = parser.add_subparsers()
    local_command = subparsers.add_parser("local")
    local_command.add_argument("--qpcr-run-path", required=True)

    local_command.add_argument("--protocol", default=None)
    local_command.add_argument("--barcodes", nargs="*")
    local_command.add_argument("--use-gdrive", action="store_true")

    accession_parser_group = local_command.add_mutually_exclusive_group()
    accession_parser_group.add_argument(
        "--plate-layout", type=FileType("rb"), dest="plate_map_file",
    )
    accession_parser_group.add_argument(
        "--well-lit", type=FileType("r"), dest="plate_map_file"
    )
    accession_parser_group.add_argument(
        "--hamilton", type=FileType("r"), dest="plate_map_file"
    )

    local_command.set_defaults(func=parse_qpcr_csv)

    gdrive_command = subparsers.add_parser("gdrive")
    gdrive_command.set_defaults(func=gdrive_processing)

    compile_accessions_command = subparsers.add_parser("compile_accessions")
    compile_accessions_command.add_argument("--run-path", required=False)
    compile_accessions_command.add_argument("--updates-only", action="store_true")
    compile_accessions_command.add_argument(
        "--sample-barcodes", required=False, nargs="*"
    )
    compile_accessions_command.set_defaults(func=compile_accessions_cli)

    args = parser.parse_args()

    if getattr(args, "func", None) is None:
        parser.print_help()
        sys.exit(2)

    args.func(args)


if __name__ == "__main__":
    main()
