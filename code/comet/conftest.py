from datetime import datetime
from pathlib import Path

import pytest
import pytz


@pytest.fixture(scope="session")
def test_data_dir():
    return Path(__file__).parent / "tests" / "data"


@pytest.fixture(scope="session")
def expected_output_data_dir():
    return Path(__file__).parent / "tests" / "expected_outputs"


@pytest.fixture(scope="session")
def input_384_plate_map(test_data_dir):
    with (test_data_dir / "COMET384-L-007.csv").open() as fh:
        yield fh


@pytest.fixture(scope="session")
def fake_dph_metadata_shipment(test_data_dir):
    with (
        test_data_dir
        / "Testing-COVID Tracker Sample Metadata (1)-6.1.2020 - Maira Phelps.xlsx"
    ).open("rb") as fh:
        yield fh


@pytest.fixture(scope="session")
def fake_dph_metadata_shipment_missing_data(test_data_dir):
    with (
        test_data_dir / "Testing-COVID Tracker Sample Metadata  MISSING DATA.xlsx"
    ).open("rb") as fh:
        yield fh


@pytest.fixture(scope="session")
def fake_collaborator_metadata_shipment(test_data_dir):
    with (test_data_dir / "Testing-Collaborator Sample Shipment.xlsx").open("rb") as fh:
        yield fh


@pytest.fixture(scope="session")
def fake_collaborator_metadata_shipment_bad_column(test_data_dir):
    with (
        test_data_dir / "Testing-Collaborator Sample Shipment - Bad Column.xlsx"
    ).open("rb") as fh:
        yield fh


@pytest.fixture(scope="session")
def time_now(test_data_dir):
    return datetime.now(pytz.timezone("US/Pacific")).strftime("%Y-%m-%d_%H:%M:%S")


@pytest.fixture(scope="session")
def fake_collaborator_metadata_shipment_missing_optional_column(test_data_dir):
    with (
        test_data_dir / "Testing-Collaborator Sample Shipment - Optional Column.xlsx"
    ).open("rb") as fh:
        yield fh


@pytest.fixture(scope="session")
def input_index_map(test_data_dir):
    with (test_data_dir / "DBP_10 - Sabrina Mann.xlsx").open("rb") as fh:
        yield fh


@pytest.fixture(scope="session")
def expected_nov_seq_output(expected_output_data_dir):
    with (
        expected_output_data_dir / "COMET384_SEQ007_DBP-10_MiSeqNovaSeq.csv"
    ).open() as fh:
        yield fh


@pytest.fixture(scope="session")
def expected_next_seq_output(expected_output_data_dir):
    with (
        expected_output_data_dir / "COMET384_SEQ007_DBP-10_iSeqNextSeq.csv"
    ).open() as fh:
        yield fh
