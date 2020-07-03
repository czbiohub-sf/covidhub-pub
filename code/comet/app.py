import json
import logging
import os

import covidhub.google.utils as gutils
from comet.lib import (
    bind_index_plate,
    concat_96_384,
    draw_96_plate_map,
    external_sample_shipment,
    metadata_lookup,
    sample_database,
    slack,
    update_ripe_samples,
)
from comet.lib.google import sheets
from covidhub.config import Config
from covidhub.google import drive
from covidhub.logging import create_logger

logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    try:
        cfg = Config()
        create_logger(cfg)
        creds = gutils.get_secrets_manager_credentials()
        os.chdir("/tmp")

        # Set up for Google Drive
        drive_service = drive.get_service(creds)
        sheets_service = sheets.get_service(creds)

        # Route based on the actions
        action = None
        if "body" in event:
            event_body = json.loads(event["body"])
            logger.info(msg=f"EVENT_BODY: {event_body}")
            action = event_body["action"]

        logger.info(msg=f"ACTION: {action}")
        if action == "external_sample_shipment":
            external_sample_shipment.handle_external_sample_shipment_request(
                cfg, drive_service, event_body
            )
        elif action == "sample_database":
            sample_database.external_sample_database(
                cfg, drive_service, sheets_service, event_body
            )
        elif action == "draw_96_plate_map":
            draw_96_plate_map.draw_96_plate_map(
                cfg, drive_service, sheets_service, event_body
            )
        elif action == "concat_96_384":
            concat_96_384.concat_96_384(cfg, drive_service, sheets_service, event_body)
        elif action == "bind_index_plate":
            bind_index_plate.handle_bind_index_plate_request(
                cfg, drive_service, sheets_service, event_body
            )
        elif action == "update_ripe_samples":
            update_ripe_samples.update_ripe_samples(
                cfg, drive_service, sheets_service, event_body
            )
        elif action == "metadata_lookup":
            metadata_lookup.metadata_lookup(
                cfg, drive_service, sheets_service, event_body
            )

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "text/html"},
            "body": "OK",
        }
    except Exception as err:
        slack.post(f"*Error in mNGS scripts:*\n{err}")
        raise


if __name__ == "__main__":
    lambda_handler({}, None)
