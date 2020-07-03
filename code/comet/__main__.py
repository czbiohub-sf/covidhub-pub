import os
import sys
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser, FileType
from pathlib import Path

from comet.lib.bind_index_plate import bind_index_local_processing
from comet.lib.concat_96_384 import concat_96_384
from comet.lib.draw_96_plate_map import draw_96_plate_map
from comet.lib.external_sample_shipment import external_sample_shipment_local_processing
from comet.lib.sample_database import external_sample_database


def main():
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--db-secret-id", dest="db_secret", default="cliahub/cliahub_test_db"
    )
    parser.add_argument("--run-path", default=Path(os.getcwd()))

    subparsers = parser.add_subparsers()

    bind_index = subparsers.add_parser("bind-index")
    bind_index.set_defaults(func=bind_index_local_processing)
    bind_index.add_argument("--plate", type=FileType("r"), dest="plate", required=True)
    bind_index.add_argument(
        "--index-map", type=FileType("rb"), dest="index_map", required=True
    )
    bind_index.add_argument("--tracking-name", required=True)

    concat = subparsers.add_parser("concat")
    concat.set_defaults(func=concat_96_384)

    sample_database = subparsers.add_parser("sample-database")
    sample_database.set_defaults(func=external_sample_database)

    draw_plate = subparsers.add_parser("draw-plate")
    draw_plate.set_defaults(func=draw_96_plate_map)

    external_shipment = subparsers.add_parser("external-shipment")
    external_shipment.set_defaults(func=external_sample_shipment_local_processing)
    external_shipment.add_argument(
        "--metadata-file", type=FileType("rb"), required=True
    )
    external_shipment.add_argument("--project-id", type=str, required=True)

    update_ripe_samples = subparsers.add_parser("update-ripe-samples")
    update_ripe_samples.set_defaults(func=update_ripe_samples)

    args = parser.parse_args()
    if getattr(args, "func", None) is None:
        parser.print_help()
        sys.exit(2)

    args.func(args)


if __name__ == "__main__":
    main()
