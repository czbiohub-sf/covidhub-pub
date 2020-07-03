import pytest

from covidhub.google.drive import (
    DriveObject,
    find_file_by_name,
    FindMode,
    mkdir,
    MultipleMatchesError,
    NoMatchesError,
    put_file,
)


@pytest.mark.integtest
def test_find_file_by_name(
    gdrive_service, gdrive_folder: DriveObject, new_filename="find_file_by_name.txt",
):
    """Tests that we can search for a file by name successfully and unsuccessfully."""
    with pytest.raises(RuntimeError):
        find_file_by_name(gdrive_service, gdrive_folder.id, new_filename)
    put_request = put_file(gdrive_service, gdrive_folder.id, new_filename)
    with put_request as fh:
        fh.write("this is random text 1")

    found_file_id = find_file_by_name(gdrive_service, gdrive_folder.id, new_filename).id
    assert put_request.id == found_file_id


@pytest.mark.integtest
def test_find_file_by_name_not_dir(
    gdrive_service,
    gdrive_folder: DriveObject,
    new_filename="find_file_by_name_not_dir.txt",
):
    """Tests that we can search for a file and not get matched to a directory that is present."""
    mkdir(gdrive_service, gdrive_folder.id, new_filename)
    with pytest.raises(RuntimeError):
        find_file_by_name(gdrive_service, gdrive_folder.id, new_filename)

    # now we put a file with the same name (yeah, google drive is weird in that this is permitted)
    put_request = put_file(gdrive_service, gdrive_folder.id, new_filename)
    with put_request as fh:
        fh.write("this is random text 1")

    found_file_id = find_file_by_name(gdrive_service, gdrive_folder.id, new_filename).id
    assert put_request.id == found_file_id


@pytest.mark.integtest
def test_find_file_by_name_most_recent(
    gdrive_service,
    gdrive_folder: DriveObject,
    filename="test_find_file_by_name_most_recent.txt",
):
    """Puts a file, and then put it again with overwrite_if_present=False.  Finding by
    filename, using require single result mode, should fail.  Finding by the filename,
    using the most recent mode, should find the second file."""
    put_request = put_file(gdrive_service, gdrive_folder.id, filename)
    with put_request as fh:
        fh.write("first")

    put_request = put_file(
        gdrive_service, gdrive_folder.id, filename, overwrite_if_present=False
    )
    with put_request as fh:
        fh.write("second")

    with pytest.raises(MultipleMatchesError):
        find_file_by_name(gdrive_service, gdrive_folder.id, filename)

    id = find_file_by_name(
        gdrive_service, gdrive_folder.id, filename, FindMode.MOST_RECENTLY_MODIFIED
    ).id
    assert id == put_request.id

    with pytest.raises(NoMatchesError):
        find_file_by_name(
            gdrive_service,
            gdrive_folder.id,
            "this_file_does_not_exist",
            FindMode.MOST_RECENTLY_MODIFIED,
        )
