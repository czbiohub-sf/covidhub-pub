import logging

import click
from IPython.terminal.embed import InteractiveShellEmbed

import covid_database.util as util
from covid_database import (
    clear_ngs_tables,
    clear_tables,
    create_tables_and_schema,
    delete_tables,
    init_db,
)
from covid_database.populate.qpcr_processing_populators.db_populator import DBPopulator
from covid_database.populate.sequencing_tracking_populators.db_populator import (
    DBPopulator as SequencingDBPopulator,
)
from covidhub.config import Config
from covidhub.google.utils import get_secrets_manager_credentials
from covidhub.logging import create_logger

log = logging.getLogger(__name__)


@click.group()
@click.option("--db-secret", default="cliahub/cliahub_test_db")
@click.option("--debug", is_flag=True)
@click.pass_context
def cliadb(ctx, db_secret, debug):
    ctx.ensure_object(dict)
    ctx.obj["CONFIG"] = Config()
    create_logger(ctx.obj["CONFIG"], debug=debug)

    log.info("Starting CLIAHub database command line tool")
    ctx.obj["ENGINE"] = init_db(util.get_db_uri(db_secret))


@cliadb.command("create")
@click.pass_context
def create_db(ctx):
    log.info("Creating all tables")
    create_tables_and_schema(ctx.obj["ENGINE"])


@cliadb.command("clear_tables")
@click.pass_context
def clear_tables_cli(ctx):
    log.info("Clearing all tables!")
    clear_tables(ctx.obj["ENGINE"])


@cliadb.command("clear_ngs_tables")
@click.pass_context
def clear_ngs_tables_cli(ctx):
    log.info("Clearing ngs tables!")
    clear_ngs_tables(ctx.obj["ENGINE"])


@cliadb.command("delete_tables")
@click.pass_context
def delete_tables_cli(ctx):
    log.info("Deleting all tables!")
    delete_tables(ctx.obj["ENGINE"])


@cliadb.command("populate")
@click.option("--google-secret", default="covid-19/google_creds")
@click.pass_context
def populate_db(ctx, google_secret):
    google_creds = get_secrets_manager_credentials(google_secret)

    db_populator = DBPopulator(google_creds, ctx.obj["CONFIG"])
    db_populator.populate_all_data()


@cliadb.command("populate_ngs")
@click.option("--google-secret", default="covid-19/google_creds")
@click.pass_context
def populate_sequencing_db(ctx, google_secret):
    google_creds = get_secrets_manager_credentials(google_secret)

    db_populator = SequencingDBPopulator(google_creds, ctx.obj["CONFIG"])
    db_populator.populate_all_data()


@cliadb.command("interact")
@click.pass_context
def interact(ctx):
    # these are injected into the IPython scope, but they appear to be unused.
    from covid_database import session_maker  # noqa: F401
    from covid_database.models import ngs_sample_tracking, qpcr_processing  # noqa: F401

    shell = InteractiveShellEmbed()
    shell()
