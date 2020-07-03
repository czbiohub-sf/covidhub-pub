import pytest

from covidhub.google.drive import (
    DriveObject,
    DriveService,
    get_contents_by_folder_id,
    get_file,
    get_file_by_name,
    put_file,
)
from covidhub.google.utils import new_http_client_from_service


@pytest.mark.integtest
def test_get_put_has_name(
    gdrive_service: DriveService,
    gdrive_folder: DriveObject,
    filename="test_get_put_has_name.txt",
):
    """Puts and gets files.  Ensure they both have sane 'name' fields for the file
    handle."""
    put_request = put_file(gdrive_service, gdrive_folder.id, filename)
    with put_request as fh:
        fh.write("hello world")
        assert fh.name is not None
    assert put_request.fh.name is not None

    # find the file and retrieve the contents.
    with get_file_by_name(gdrive_service, gdrive_folder.id, filename) as fh:
        assert fh.read() == "hello world"
        assert fh.name is not None


@pytest.mark.integtest
def test_put_guess_mimetype(
    gdrive_service: DriveService,
    gdrive_folder: DriveObject,
    filename="test_put_guess_mimetype.txt",
):
    """Puts a file, guessing the mimetype from the filename, and ensure we can
    see the file."""
    put_request = put_file(gdrive_service, gdrive_folder.id, filename)
    with put_request as fh:
        fh.write("hello world")

    # find the file and retrieve the contents.
    with get_file_by_name(gdrive_service, gdrive_folder.id, filename) as fh:
        assert fh.read() == "hello world"


@pytest.mark.integtest
def test_put_override_content_type(
    gdrive_service: DriveService,
    gdrive_folder: DriveObject,
    filename="test_put_override_content_type.txt",
):
    """Puts a file, and ensure we can see the file."""
    put_request = put_file(
        gdrive_service,
        gdrive_folder.id,
        filename,
        content_type="application/i-made-this-up",
    )
    with put_request as fh:
        fh.write(b"hello world")

    # find the file and retrieve the contents.  because the content-type is
    # set to a binary one, we should get back binary data.
    with get_file_by_name(gdrive_service, gdrive_folder.id, filename) as fh:
        assert fh.read() == b"hello world"


@pytest.mark.integtest
def test_put_enforce_binary(
    gdrive_service: DriveService,
    gdrive_folder: DriveObject,
    filename="test_put_enforce_binary.txt",
):
    """Puts a file, and ensure we can see the file."""
    put_request = put_file(gdrive_service, gdrive_folder.id, filename, binary=True)
    with put_request as fh:
        fh.write(b"hello world")

    # find the file and retrieve the contents.  because the content-type is
    # guessed, we still get back a text file.
    with get_file_by_name(gdrive_service, gdrive_folder.id, filename) as fh:
        assert fh.read() == "hello world"


@pytest.mark.integtest
def test_put_no_overwrite(
    gdrive_service: DriveService,
    gdrive_folder: DriveObject,
    filename="test_put_no_overwrite.txt",
):
    """Puts a file, and then put it again with overwrite_if_present=False.
    Both files should be found."""
    put_request = put_file(gdrive_service, gdrive_folder.id, filename)
    with put_request as fh:
        fh.write("first")

    put_request = put_file(
        gdrive_service, gdrive_folder.id, filename, overwrite_if_present=False
    )
    with put_request as fh:
        fh.write("second")

    listing = get_contents_by_folder_id(
        gdrive_service, gdrive_folder.id, only_files=True
    )
    matching_listings = [entry for entry in listing if entry.name == filename]
    assert len(matching_listings) == 2


@pytest.mark.integtest
def test_put_overwrite_simple(
    gdrive_service: DriveService,
    gdrive_folder: DriveObject,
    filename="test_put_overwrite_simple.txt",
):
    """Puts a file, and then put it again with overwrite_if_present=True.  Only
    one file should be found."""
    put_request = put_file(gdrive_service, gdrive_folder.id, filename)
    with put_request as fh:
        fh.write("first")

    put_request = put_file(
        gdrive_service, gdrive_folder.id, filename, overwrite_if_present=True
    )
    with put_request as fh:
        fh.write("second")

    listing = get_contents_by_folder_id(
        gdrive_service, gdrive_folder.id, only_files=True
    )
    matching_listings = [entry for entry in listing if entry.name == filename]
    assert len(matching_listings) == 1


@pytest.mark.integtest
def test_put_overwrite_multiple(
    gdrive_service: DriveService,
    gdrive_folder: DriveObject,
    filename="test_put_overwrite_multiple.txt",
):
    """Test the case where we are overwriting and there are multiple files we
    could possibly overwrite.  It should overwrite the newest file."""
    put_request = put_file(gdrive_service, gdrive_folder.id, filename)
    with put_request as fh:
        fh.write("first")
    first_id = put_request.id

    put_request = put_file(
        gdrive_service, gdrive_folder.id, filename, overwrite_if_present=False
    )
    with put_request as fh:
        fh.write("second")
    second_id = put_request.id

    put_request = put_file(
        gdrive_service, gdrive_folder.id, filename, overwrite_if_present=True
    )
    with put_request as fh:
        fh.write("third")
    assert put_request.id == second_id

    listing = get_contents_by_folder_id(
        gdrive_service, gdrive_folder.id, only_files=True
    )
    matching_listings = [entry for entry in listing if entry.name == filename]
    assert len(matching_listings) == 2

    with get_file(gdrive_service, first_id, True) as fh:
        assert fh.read() == b"first"
    with get_file(gdrive_service, second_id, False) as fh:
        assert fh.read() == "third"


@pytest.mark.integtest
def test_put_read_after(
    gdrive_service: DriveService,
    gdrive_folder: DriveObject,
    filename="test_put_read_after.txt",
):
    """Puts a file and ensure we can read what was written to the file."""
    put_request = put_file(gdrive_service, gdrive_folder.id, filename)
    with put_request as fh:
        fh.write("hello world")

    # find the file and retrieve the contents.
    with get_file_by_name(gdrive_service, gdrive_folder.id, filename) as fh:
        assert fh.read() == "hello world"

    with put_request as fh:
        assert fh.read() == "hello world"


@pytest.mark.integtest
def test_get_put_http_client(
    gdrive_service: DriveService,
    gdrive_folder: DriveObject,
    filename="test_get_put_http_client.txt",
):
    """Puts a file.  Then retrieve the file using a custom HTTP client."""
    put_request = put_file(gdrive_service, gdrive_folder.id, filename)
    with put_request as fh:
        fh.write("hello world")
        assert fh.name is not None
    assert put_request.fh.name is not None

    # instantiate a new http client with the same credentials.
    http = new_http_client_from_service(gdrive_service)
    # find the file and retrieve the contents.
    with get_file_by_name(gdrive_service, gdrive_folder.id, filename, http=http) as fh:
        assert fh.read() == "hello world"
        assert fh.name is not None
