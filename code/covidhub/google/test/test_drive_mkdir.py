import pytest

from covidhub.google.drive import (
    DriveObject,
    DriveService,
    get_folder_id_of_path,
    mkdir,
    mkdir_recursive,
)


@pytest.mark.integtest
def test_mkdir(
    gdrive_service: DriveService,
    gdrive_folder: DriveObject,
    new_folder_name="mkdir-test",
):
    subdir = mkdir(gdrive_service, gdrive_folder.id, new_folder_name)
    traversed_folder_id = get_folder_id_of_path(
        gdrive_service, [gdrive_folder.name, new_folder_name]
    )
    assert subdir.id == traversed_folder_id


@pytest.mark.integtest
def test_mkdir_recursive(
    gdrive_service: DriveService,
    gdrive_folder: DriveObject,
    new_folder_name="mkdir-recursive",
):
    new_path_components = [new_folder_name, "abc", "abc", "def"]
    full_path = [gdrive_folder.name] + new_path_components
    subdir_id = mkdir_recursive(gdrive_service, gdrive_folder.id, new_path_components)
    lookup = get_folder_id_of_path(gdrive_service, full_path)

    assert subdir_id == lookup

    second_subdir_id = mkdir_recursive(
        gdrive_service, gdrive_folder.id, new_path_components
    )

    assert second_subdir_id == lookup
