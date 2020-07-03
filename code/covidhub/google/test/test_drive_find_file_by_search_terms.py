import pytest

from covidhub.google.drive import (
    DriveObject,
    DriveService,
    find_file_by_search_terms,
    mkdir,
    put_file,
)


@pytest.mark.integtest
def test_find_file_by_search_terms(
    gdrive_service: DriveService,
    gdrive_folder: DriveObject,
    subdir="test_find_file_by_search_terms",
    search_terms=("hello", "world", "who"),
    filenames=("hello____world-who.txt", "hello____world----who.txt"),
):
    """Search for files by search terms."""

    subdir = mkdir(gdrive_service, gdrive_folder.id, subdir)

    put_request = put_file(gdrive_service, subdir.id, filenames[0])
    with put_request as fh:
        fh.write("this is random text 1")

    # find the file and retrieve the contents.
    result = find_file_by_search_terms(gdrive_service, subdir.id, search_terms)
    assert result.id == put_request.id

    # find the file and retrieve the contents.  this should fail because we
    # have an extra term that is not satisfied.
    with pytest.raises(RuntimeError):
        result = find_file_by_search_terms(
            gdrive_service, subdir.id, search_terms + ("chicken",)
        )

    put_request = put_file(gdrive_service, subdir.id, filenames[1])
    with put_request as fh:
        fh.write("this is random text 2")

    # find the file and retrieve the contents.  this should fail because we
    # now have multiple matching files.
    with pytest.raises(RuntimeError):
        result = find_file_by_search_terms(gdrive_service, subdir.id, search_terms)


@pytest.mark.integtest
def test_find_file_by_search_terms_exclude_contents(
    gdrive_service: DriveService,
    gdrive_folder: DriveObject,
    subdir="test_find_file_by_search_terms_exclude_contents",
    search_terms=("hello", "world", "who"),
    filenames=("keywords_not_in_filename.txt", "hello____world----who.txt"),
):
    """Search for files by search terms."""

    subdir = mkdir(gdrive_service, gdrive_folder.id, subdir)

    put_request = put_file(gdrive_service, subdir.id, filenames[0])
    with put_request as fh:
        fh.write(" ".join(search_terms))

    put_request = put_file(gdrive_service, subdir.id, filenames[1])
    with put_request as fh:
        fh.write("this is random text 2")

    # find the file and retrieve the contents.
    result = find_file_by_search_terms(gdrive_service, subdir.id, search_terms)
    assert result.id == put_request.id
