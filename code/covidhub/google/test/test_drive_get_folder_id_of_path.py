import pytest

from covidhub.google.drive import DriveObject, DriveService, get_folder_id_of_path


@pytest.mark.integtest
def test_get_folder_id_of_path_one_level(
    gdrive_service: DriveService, gdrive_folder: DriveObject
):
    """Tests that get_folder_id_of_path works with an unnested folder."""
    retrieved_folder_id = get_folder_id_of_path(gdrive_service, [gdrive_folder.name])
    assert retrieved_folder_id == gdrive_folder.id
