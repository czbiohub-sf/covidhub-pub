import logging

import covid_database.util as util
from covid_database import (
    create_tables_and_schema,
    delete_tables,
    init_db,
    session_scope,
)
from covid_database.populate.qpcr_processing_populators.db_populator import DBPopulator
from covid_database.populate.sequencing_tracking_populators.db_populator import (
    DBPopulator as SequencingDBPopulator,
)
from covidhub.config import Config
from covidhub.google.utils import get_secrets_manager_credentials
from covidhub.logging import create_logger

log = logging.getLogger(__name__)


def lambda_handler(event, context):
    cfg = Config()
    create_logger(cfg)

    log.info("Starting DB population process")
    engine = init_db(util.get_db_uri(f"cliahub/cliahub_{cfg.aws_env}"))

    log.debug("Getting google credentials")
    google_creds = get_secrets_manager_credentials()

    if event.get("CLEAR_DATABASE", False):
        log.info("Deleting existing tables")
        delete_tables(engine)

        log.info("Recreating schema")
        create_tables_and_schema(engine)

    with session_scope():
        log.info("Populating DB")
        db_populator = DBPopulator(google_creds, cfg)
        db_populator.populate_all_data()

        ngs_populator = SequencingDBPopulator(google_creds, cfg)
        ngs_populator.populate_all_data()
