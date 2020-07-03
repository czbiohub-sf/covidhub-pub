import pytest

from covidhub.google.drive import (
    DriveObject,
    DriveService,
    get_contents_by_folder_id,
    mkdir,
    put_file,
)


@pytest.mark.integtest
def test_get_contents_by_folder_id_types(
    gdrive_service: DriveService,
    gdrive_folder: DriveObject,
    new_folder_name="test_get_contents_by_folder_id_types",
):
    """Verify that get_contents_by_folder_id can filter by only files correctly."""
    subdir = mkdir(gdrive_service, gdrive_folder.id, new_folder_name)

    # put a file and subdirectory there.
    with put_file(gdrive_service, subdir.id, "file") as fh:
        fh.write(b"this is a file")

    mkdir(gdrive_service, subdir.id, "another-subdir")

    results = get_contents_by_folder_id(gdrive_service, subdir.id, only_files=True)
    assert len(results) == 1
    assert results[0].name == "file"

    results = get_contents_by_folder_id(gdrive_service, subdir.id, only_files=False)
    assert len(results) == 2
    assert any(result.name == "file" for result in results)
    assert any(result.name == "another-subdir" for result in results)


@pytest.mark.integtest
def test_get_contents_by_folder_id_paging(
    gdrive_service: DriveService,
    gdrive_folder: DriveObject,
    new_folder_name="test_get_contents_by_folder_id_paging",
):
    """Verify that get_contents_by_folder_id can iterate through pages of results correctly."""
    subdir = mkdir(gdrive_service, gdrive_folder.id, new_folder_name)

    # put two files there.
    with put_file(gdrive_service, subdir.id, "file0") as fh:
        fh.write(b"this is a file")
    with put_file(gdrive_service, subdir.id, "file1") as fh:
        fh.write(b"this is a file")

    # even with page_size=1, we should be able to retrieve all the results.
    results = get_contents_by_folder_id(
        gdrive_service, subdir.id, only_files=True, page_size=1
    )
    assert len(results) == 2
