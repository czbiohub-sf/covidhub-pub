from contextlib import contextmanager
from pathlib import Path

import sqlalchemy
import sqlalchemy.orm
from pkg_resources import resource_filename
from sqlalchemy.sql import text
from sqlalchemy.sql.ddl import DDL

import covid_database.models as models

# type alias for brevity in hints
Engine = sqlalchemy.engine.Engine

session_maker = sqlalchemy.orm.sessionmaker()


def init_db(db_uri: str) -> Engine:
    db = sqlalchemy.create_engine(db_uri)
    session_maker.configure(bind=db)
    return db


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = session_maker()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_permissions(session, schema):
    """This function renews the read permissions for the read-only user"""
    for statement in (
        f"GRANT USAGE ON SCHEMA {schema} TO cliahub",
        f"GRANT SELECT ON ALL TABLES IN SCHEMA {schema} TO cliahub",
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT SELECT ON TABLES TO cliahub",
    ):
        session.execute(statement)


def create_tables_and_schema(engine: Engine):
    """Creates the schema and all tables"""
    with session_scope() as session:
        sqlalchemy.event.listen(
            models.qpcr_processing.QPCRProcessingBase.metadata,
            "before_create",
            DDL("CREATE SCHEMA IF NOT EXISTS qpcr_processing"),
        )
        models.qpcr_processing.QPCRProcessingBase.metadata.create_all(bind=engine)
        reset_permissions(session, "qpcr_processing")
        sqlalchemy.event.listen(
            models.ngs_sample_tracking.NGSTrackingBase.metadata,
            "before_create",
            DDL("CREATE SCHEMA IF NOT EXISTS ngs_sample_tracking"),
        )
        models.ngs_sample_tracking.NGSTrackingBase.metadata.create_all(bind=engine)
        reset_permissions(session, "ngs_sample_tracking")

        sqlalchemy.event.listen(
            models.covidtracker.CovidTrackerBase.metadata,
            "before_create",
            DDL("CREATE SCHEMA IF NOT EXISTS covidtracker"),
        )
        models.covidtracker.CovidTrackerBase.metadata.create_all(bind=engine)
        reset_permissions(session, "covidtracker")


def clear_tables(engine: Engine):
    """Deletes all records from all tables but does not delete the tables schema"""
    clear_ngs_tables(engine)
    clear_qpcr_tables(engine)
    clear_covidtracker_tables(engine)


def clear_qpcr_tables(engine: Engine):
    """Deletes all records from qpcr tables but does not delete the tables schema"""
    for tbl in reversed(
        models.qpcr_processing.QPCRProcessingBase.metadata.sorted_tables
    ):
        engine.execute(tbl.delete())


def clear_ngs_tables(engine: Engine):
    """Deletes all records from ngs tracking tables but does not delete the tables schema"""
    for tbl in reversed(
        models.ngs_sample_tracking.NGSTrackingBase.metadata.sorted_tables
    ):
        engine.execute(tbl.delete())


def clear_covidtracker_tables(engine: Engine):
    """Deletes all records from covidtracker tables but does not delete the tables schema"""
    for tbl in reversed(models.covidtracker.CovidTrackerBase.metadata.sorted_tables):
        engine.execute(tbl.delete())


def delete_tables(engine: Engine):
    """Deletes all tables from DB"""
    with engine.connect() as con:
        con.execute(text("DROP schema IF EXISTS qpcr_processing CASCADE;"))
        con.execute(text("DROP schema IF EXISTS ngs_sample_tracking CASCADE;"))
        con.execute(text("DROP schema IF EXISTS covidtracker CASCADE;"))
        for typname in con.execute(
            "select typname from pg_catalog.pg_type where typtype = 'e'"
        ):
            con.execute(f"DROP TYPE {typname[0]} CASCADE;")
