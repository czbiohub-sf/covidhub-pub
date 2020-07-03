import uuid

import pytest
from google.oauth2 import service_account

from covidhub.google.drive import (
    DriveObject,
    DriveService,
    get_service,
    mkdir,
    NUM_RETRIES,
)
from covidhub.google.utils import get_secrets_manager_credentials


def credentials_for_tests() -> service_account.Credentials:
    return get_secrets_manager_credentials(secret_id="covid-19/google_test_creds")


@pytest.fixture(scope="session")
def gdrive_service():
    """This fixture sets up a gdrive service object."""
    return get_service(credentials_for_tests())


@pytest.fixture(scope="session")
def gdrive_folder(gdrive_service: DriveService) -> DriveObject:
    """This fixture sets up a folder with a unique name on gdrive and removes it and its contents at
    the end of the test.  The folder will always be at the top level of the account, i.e., the
    folder's parent is `root`.  A DriveObject object is returned."""
    name = f"TEST-PLEASE-DELETE-ME-{uuid.uuid4()}"
    drive_folder = mkdir(gdrive_service, "root", name)
    yield drive_folder

    gdrive_service.files().delete(fileId=drive_folder.id).execute(
        num_retries=NUM_RETRIES
    )
