import contextlib
import socket
import subprocess
import time
from dataclasses import dataclass
from uuid import uuid4

import pytest
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

import covid_database

USERNAME = "cliahub_rw"
PASSWORD = "cliahub_rw"


@dataclass
class PostgresInstance:
    container_id: str
    port: int


@dataclass
class PostgresDatabase(PostgresInstance):
    database_name: str

    def as_uri(self):
        return f"postgresql://{USERNAME}:{PASSWORD}@localhost:{self.port}/{self.database_name}"


@pytest.fixture(scope="session")
def unused_tcp_port():
    with contextlib.closing(socket.socket()) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def postgres_instance(unused_tcp_port) -> PostgresInstance:
    """Starts a postgres instance with username/password cliadb/cliadb.  Returns a tuple
    consisting of the container id, and the port the postgres instance can be reached
    at."""
    process = subprocess.run(
        [
            "docker",
            "create",
            "-p",
            f"{unused_tcp_port}:5432",
            "-e",
            f"POSTGRES_USER={USERNAME}",
            "-e",
            f"POSTGRES_PASSWORD={PASSWORD}",
            "postgres:11.5-alpine",
        ],
        stdout=subprocess.PIPE,
    )
    container_id = process.stdout.decode("utf-8").strip()

    subprocess.check_call(["docker", "start", container_id])
    time.sleep(3)

    # create the cliahub user.  we don't use this in tests, but the schema creation code
    # will muck around with this user's permissions.
    subprocess.check_call(
        [
            "docker",
            "exec",
            f"{container_id}",
            "psql",
            "-p",
            "5432",
            "-U",
            USERNAME,
            "-c",
            "CREATE USER cliahub",
        ],
    )

    yield PostgresInstance(container_id, unused_tcp_port)

    subprocess.check_call(["docker", "stop", container_id])
    subprocess.check_call(["docker", "rm", container_id])


@pytest.fixture()
def postgres_database(postgres_instance) -> PostgresDatabase:
    """Starts a postgres database.  Returns a tuple consisting of the container id, the
    port the postgres instance can be reached at, and the name of the database."""

    safe_uuid = str(uuid4()).replace("-", "_")
    db_name = f"db_{safe_uuid}"
    subprocess.check_call(
        [
            "docker",
            "exec",
            f"{postgres_instance.container_id}",
            "psql",
            "-p",
            "5432",
            "-U",
            USERNAME,
            "-c",
            f"CREATE DATABASE {db_name}",
        ],
    )

    yield PostgresDatabase(
        postgres_instance.container_id, postgres_instance.port, db_name
    )


@pytest.fixture()
def postgres_database_with_schema(postgres_database) -> PostgresDatabase:
    db = covid_database.init_db(postgres_database.as_uri())
    covid_database.create_tables_and_schema(db)
    yield postgres_database


@pytest.fixture()
def connection(postgres_database_with_schema) -> Connection:
    db = covid_database.init_db(postgres_database_with_schema.as_uri())
    connection = db.connect()

    yield connection

    connection.close()


@pytest.fixture()
def session(connection) -> Session:
    transaction = connection.begin()
    session = covid_database.session_maker()

    yield session

    session.close()
    transaction.commit()
