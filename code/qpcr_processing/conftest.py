import json
from pathlib import Path

import pytest
from google.oauth2 import service_account

import covidhub.conftest
from covidhub.collective_form import CollectiveForm
from covidhub.config import AlternateGDriveConfig, Config
from covidhub.constants.controls import STANDARD_CONTROL_WELLS
from covidhub.constants.enums import ControlsMappingType
from covidhub.constants.qpcr_forms import SampleMetadata
from covidhub.google.drive import DriveObject, NUM_RETRIES, put_file
from covidhub.google.utils import get_secrets_manager_credentials
from qpcr_processing.control_wells import get_control_wells_from_type

# this is just to make flake8 shut up
gdrive_service = covidhub.conftest.gdrive_service
gdrive_folder = covidhub.conftest.gdrive_folder


@pytest.fixture(scope="session")
def test_data_dir():
    return Path(__file__).parent / "test" / "data"


def credentials_for_tests() -> service_account.Credentials:
    return get_secrets_manager_credentials(secret_id="covid-19/google_test_creds")


@pytest.fixture(scope="session")
def google_sheets(gdrive_service, drive_folder_scoped_config):
    """This fixture returns a google sheets object."""
    cfg = drive_folder_scoped_config
    collective_form = CollectiveForm(
        gdrive_service, cfg["DATA"]["collection_form_spreadsheet_id"]
    )

    return collective_form


@pytest.fixture(scope="session")
def sample_metadata_sheet(google_sheets):
    return google_sheets[SampleMetadata.SHEET_NAME]


@pytest.fixture(scope="session")
def hamilton_plate_layout(test_data_dir):
    with (test_data_dir / "hamilton_plate_layout.csv").open() as fh:
        yield fh


@pytest.fixture(scope="session")
def expected_hamilton_accession_data():
    accession_data = {
        "B1": "S47399",
        "C1": "S46989",
        "D1": "S46688",
        "E1": "S46667",
        "F1": "S46956",
        "G1": "S46988",
        "A2": "S46963",
        "B2": "S47089",
        "C2": "S46941",
        "D2": "S46860",
        "E2": "S46951",
        "F2": "S46964",
        "G2": "S46689",
        "H2": "S47234",
        "A3": "S47276",
        "B3": "S47628",
        "C3": "S47624",
        "D3": "S47264",
        "E3": "S47579",
        "F3": "S47574",
        "G3": "S47623",
        "H3": "S47359",
    }

    accession_data.update(STANDARD_CONTROL_WELLS)

    return accession_data


@pytest.fixture(scope="session")
def bad_hamilton_layout(test_data_dir):
    with (test_data_dir / "bad_hamilton_layout.csv").open() as fh:
        yield fh


@pytest.fixture(scope="session")
def welllit_plate_layout(test_data_dir):
    with (test_data_dir / "welllit_plate_layout.csv").open() as fh:
        yield fh


@pytest.fixture(scope="session")
def expected_welllit_accession_data():
    accession_data = {
        "B1": "ACCTEST1",
        "C1": "ACCTEST2",
        "E1": "ACCTEST3",
        "F1": "ACCTEST4",
        "G1": "ACCTEST6",
        "F2": "ACCTEST5",
        "G7": "ACCTEST7",
    }

    accession_data.update(STANDARD_CONTROL_WELLS)

    return accession_data


@pytest.fixture(scope="session")
def bad_welllit_layout(test_data_dir):
    with (test_data_dir / "bad_welllit_layout.csv").open() as fh:
        yield fh


@pytest.fixture(scope="session")
def legacy_plate_layout(test_data_dir):
    with (test_data_dir / "legacy_plate_layout.xlsx").open("rb") as fh:
        yield fh


@pytest.fixture(scope="session")
def expected_legacy_accession_data(test_data_dir):
    with (test_data_dir / "expected_legacy_accession.json").open() as fh:
        return json.load(fh)


@pytest.fixture(scope="session")
def sample_plate_barcode():
    """Return a sample plate barcode.
    Right now it's just a hardcoded value."""
    return "SP000120120"


@pytest.fixture(scope="session")
def validation_plate_barcode():
    return "VP000120120"


@pytest.fixture(scope="session")
def standard_control_wells():
    """Return standard"""
    return get_control_wells_from_type(ControlsMappingType.Standard)


@pytest.fixture(scope="function")
def gdrive_hamilton_folder(
    gdrive_service, gdrive_folder, hamilton_plate_layout, sample_plate_barcode
):
    """This fixture creates a WellLit plate layout file and then removes it at
    the end."""
    put_request = put_file(
        gdrive_service,
        gdrive_folder.id,
        f"test_04082020-173053_{sample_plate_barcode}_hamilton - Hanna Retallack.csv",
        binary=False,
    )

    hamilton_plate_layout.seek(0)
    with put_request as fh:
        for line in hamilton_plate_layout:
            fh.write(line)

    yield gdrive_folder.id

    gdrive_service.files().delete(fileId=put_request.id).execute(
        num_retries=NUM_RETRIES
    )


@pytest.fixture(scope="function")
def gdrive_welllit_folder(
    gdrive_service, gdrive_folder, welllit_plate_layout, sample_plate_barcode
):
    """This fixture creates a WellLit plate layout file and then removes it at
    the end."""
    put_request = put_file(
        gdrive_service,
        gdrive_folder.id,
        f"test_welllit_{sample_plate_barcode}_plate_layout.csv",
        binary=False,
    )

    welllit_plate_layout.seek(0)
    with put_request as fh:
        for line in welllit_plate_layout:
            fh.write(line)

    yield gdrive_folder.id

    gdrive_service.files().delete(fileId=put_request.id).execute(
        num_retries=NUM_RETRIES
    )


@pytest.fixture(scope="function")
def gdrive_legacy_folder(
    gdrive_service, gdrive_folder, legacy_plate_layout, sample_plate_barcode
):
    """This fixture creates a legacy plate layout file and then removes it at
    the end."""
    put_request = put_file(
        gdrive_service,
        gdrive_folder.id,
        f"test_welllit_{sample_plate_barcode}_plate_layout.xlsx",
        binary=True,
    )

    legacy_plate_layout.seek(0)
    with put_request as fh:
        for line in legacy_plate_layout:
            fh.write(line)

    yield gdrive_folder.id

    gdrive_service.files().delete(fileId=put_request.id).execute(
        num_retries=NUM_RETRIES
    )


@pytest.fixture(scope="session")
def drive_folder_scoped_config(gdrive_folder: DriveObject) -> Config:
    """set up a config that overrides the normal drive path to point at the test arena
    we've set up."""
    return AlternateGDriveConfig(gdrive_folder.name)


def pcr_and_sample_barcode_with_bravo_rna_entry():
    return "B132314", "SP000139"


def pcr_and_sample_barcode_for_rerun_only():
    return "B131390", "VP000004"
