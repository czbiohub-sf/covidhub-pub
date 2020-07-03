import contextlib
import io
import mimetypes
from dataclasses import dataclass
from enum import auto, Enum
from typing import IO, List, Optional, Sequence
from urllib.parse import parse_qs, urlparse

import googleapiclient.discovery
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from httplib2 import Http

GDRIVE_FOLDER_MIMETYPE = "application/vnd.google-apps.folder"
GDRIVE_ID_FORMAT_STRING = "https://drive.google.com/open?id={}"
GDRIVE_FIELDS = "files(name, id, mimeType, modifiedTime, md5Checksum)"
NUM_RETRIES = 5


# type alias for readability
DriveService = googleapiclient.discovery.Resource


@dataclass(frozen=True)
class DriveObject:
    drive_service: DriveService
    id: str
    name: str
    mimeType: str
    modifiedTime: Optional[str] = None
    md5Checksum: Optional[str] = None

    @property
    def is_dir(self):
        return self.mimeType == GDRIVE_FOLDER_MIMETYPE

    def open(self, mode=None):
        if mode is None:
            # do your best to sniff the file type
            mode = "r" if self.mimeType.startswith("text/") else "rb"

        if mode == "r":
            return get_file(self.drive_service, self.id, binary=False)
        elif mode == "rb":
            return get_file(self.drive_service, self.id, binary=True)
        else:
            raise ValueError(f"mode '{mode}' not supported by this method")


class FindMode(Enum):
    """When find_file_by_name is called with this mode, we require that there is a
    single result, and we return that.  If there are zero results, a RuntimeError is
    raised.  If there are more than one results, a MultipleMatchesError is raised."""

    REQUIRE_SINGLE_RESULT = auto()

    """When find_file_by_name is called with this mode, we require that there is one
    or more results.  If there are zero results, a RuntimeError is raised.  Otherwise,
    the file with the most recently modified timestamp is returned."""
    MOST_RECENTLY_MODIFIED = auto()


def get_service(google_credentials: service_account.Credentials) -> DriveService:
    """Retrieves a gdrive service object."""
    service = googleapiclient.discovery.build(
        "drive",
        "v3",
        credentials=google_credentials.with_scopes(
            ["https://www.googleapis.com/auth/drive"]
        ),
        cache_discovery=False,
    )
    return service


class MultipleMatchesError(RuntimeError):
    """Raised if there are multiple matches when searching a folder for a specific file."""

    ...


class NoMatchesError(RuntimeError):
    """Raised if there are no matches when searching a folder for a specific file."""

    ...


def _q_escape(query):
    return query.replace("'", "\\'")


def _filter_results(results, find_error_message, find_mode: FindMode):
    if len(results) == 0:
        raise NoMatchesError("No matches for {}".format(find_error_message))
    if find_mode == FindMode.REQUIRE_SINGLE_RESULT and len(results) > 1:
        raise MultipleMatchesError(
            "Found multiple matches for {}".format(find_error_message)
        )
    return results[0]


def get_folder_id_of_path(
    service: DriveService, path_components: List[str], parent_id: str = None
) -> str:
    """Given sequence of path components, resolve a folder's path to an ID. Each path
    component must be resolved uniquely (i.e., there cannot be more than one folder in
    its parent that has the same name. If a path component cannot be resolved uniquely,
    MultipleMatchesError is raised."""
    if len(path_components) == 0:
        if parent_id is not None:
            return parent_id
        else:
            return "root"

    if parent_id is None:
        query = "('root' in parents OR sharedWithMe = true)"
    else:
        query = f"'{_q_escape(parent_id)}' in parents"
    query = (
        query + f" AND name = '{_q_escape(path_components[0])}'"
        f" AND mimeType = '{GDRIVE_FOLDER_MIMETYPE}'"
        f" AND trashed = false"
    )
    results = (
        service.files()
        .list(
            q=query,
            corpora="allDrives",
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
        )
        .execute(num_retries=NUM_RETRIES)
    )
    files = results["files"]
    result = _filter_results(
        files, f"folder name = '{path_components[0]}'", FindMode.REQUIRE_SINGLE_RESULT
    )

    return get_folder_id_of_path(service, path_components[1:], result["id"])


def get_contents_by_folder_id(
    service: DriveService,
    folder_id: str = None,
    *,
    only_files: bool = False,
    page_size: int = 100,
) -> List[DriveObject]:
    """Given an ID of a folder, return a list of the contents."""
    query = f"'{_q_escape(folder_id)}' in parents AND trashed = false"
    if only_files:
        query = query + f" AND mimeType != '{GDRIVE_FOLDER_MIMETYPE}'"
    page_token = None
    accumulator = []
    while True:
        results = (
            service.files()
            .list(
                q=query,
                pageSize=page_size,
                pageToken=page_token,
                fields=f"{GDRIVE_FIELDS},nextPageToken",
            )
            .execute(num_retries=NUM_RETRIES)
        )
        accumulator.extend(
            DriveObject(drive_service=service, **entry) for entry in results["files"]
        )
        page_token = results.get("nextPageToken", None)
        if page_token is None:
            break

    return accumulator


def find_file_by_id(service: DriveService, file_id: str) -> DriveObject:
    """Given a file id, return a DriveObject. Useful if you don't know the filename/type
    """
    file_entry = service.files().get(fileId=file_id).execute()

    return DriveObject(
        drive_service=service,
        id=file_entry["id"],
        name=file_entry["name"],
        mimeType=file_entry["mimeType"],
    )


def find_file_by_name(
    service: DriveService,
    folder_id: str,
    file_name: str,
    find_mode: FindMode = FindMode.REQUIRE_SINGLE_RESULT,
    *,
    http: Optional[Http] = None,
) -> DriveObject:
    """Given a name of a file, return its id, and modifiedTime."""
    query = (
        f"'{_q_escape(folder_id)}' in parents"
        f" AND trashed = false"
        f" AND name = '{_q_escape(file_name)}'"
        f" AND mimeType != '{GDRIVE_FOLDER_MIMETYPE}'"
    )
    results = (
        service.files()
        .list(q=query, orderBy="modifiedTime desc", fields=GDRIVE_FIELDS)
        .execute(num_retries=NUM_RETRIES, http=http)["files"]
    )
    result = _filter_results(results, f"file name = '{file_name}'", find_mode)

    return DriveObject(drive_service=service, **result)


def find_file_by_search_terms(
    service: DriveService,
    folder_id: str,
    search_terms: Sequence[str],
    find_mode: FindMode = FindMode.REQUIRE_SINGLE_RESULT,
) -> DriveObject:
    """Given part of a file name check if it exists and return file information.
    Returns a dictionary with "id" and "name".  If there are multiple matches for the
    search terms, MultipleMatchesError is raised.

    Please note that this is a filename-based search, and not a content-based search.
    """
    if isinstance(search_terms, str):
        raise ValueError("Search terms should be a sequence of strings")

    fulltext_search_term = " ".join(search_terms)
    query = (
        f"'{_q_escape(folder_id)}' in parents"
        f" AND trashed = false "
        f" AND fullText contains '{_q_escape(fulltext_search_term)}'"
        f" AND mimeType != '{GDRIVE_FOLDER_MIMETYPE}'"
    )
    results = (
        service.files()
        .list(q=query, fields=GDRIVE_FIELDS)
        .execute(num_retries=NUM_RETRIES)["files"]
    )
    filtered_results = [
        file
        for file in results
        if all([search_term in file["name"] for search_term in search_terms])
    ]
    result = _filter_results(
        filtered_results, f"search terms '{search_terms}'", find_mode,
    )
    return DriveObject(drive_service=service, **result)


def get_child_by_name(
    service: DriveService, folder_id: str, name: str
) -> List[DriveObject]:
    """Given a name of a child, return its id and content-type."""
    query = (
        f"'{_q_escape(folder_id)}' in parents"
        f" AND trashed = false"
        f" AND name = '{_q_escape(name)}'"
    )
    return [
        DriveObject(drive_service=service, **entry)
        for entry in service.files()
        .list(q=query, fields=GDRIVE_FIELDS)
        .execute(num_retries=NUM_RETRIES)["files"]
    ]


@contextlib.contextmanager
def get_file_by_name(
    service: DriveService,
    folder_id: str,
    file_name: str,
    find_mode: FindMode = FindMode.REQUIRE_SINGLE_RESULT,
    *,
    http: Optional[Http] = None,
) -> IO:
    """Given a name of a file, return its contents.  If there are multiple files in the
    folder with the same name, MultipleMatchesError is raised unless FindMode = MOST_RECENTLY_MODIFIED"""
    query = (
        f"'{_q_escape(folder_id)}' in parents"
        f" AND trashed = false"
        f" AND name = '{_q_escape(file_name)}'"
        f" AND mimeType != '{GDRIVE_FOLDER_MIMETYPE}'"
    )
    results = (
        service.files()
        .list(q=query, orderBy="modifiedTime desc", fields="files(id, mimeType)")
        .execute(num_retries=NUM_RETRIES, http=http)["files"]
    )
    result = _filter_results(results, f"file name = '{file_name}'", find_mode)

    with get_file(
        service, result["id"], not result["mimeType"].startswith("text/"), http=http
    ) as fh:
        yield fh


@contextlib.contextmanager
def get_file(
    service: DriveService,
    file_id: str,
    binary: Optional[bool] = None,
    *,
    http: Optional[Http] = None,
) -> IO:
    """Given an ID of a file, return its contents."""
    if binary is None:
        mimeType = (
            service.files()
            .get(fileId=file_id)
            .execute(num_retries=NUM_RETRIES, http=http)["mimeType"]
        )
        binary = not mimeType.startswith("text/")

    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    fh.name = GDRIVE_ID_FORMAT_STRING.format(file_id)
    assert request.http is not None
    if http is not None:
        request.http = http
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk(num_retries=NUM_RETRIES)

    fh.seek(0)
    if binary:
        yield fh
    else:
        yield io.TextIOWrapper(fh)

    fh.close()


class put_file:
    def __init__(
        self,
        service,
        folder_id,
        filename,
        content_type=None,
        binary=None,
        overwrite_if_present=True,
    ):
        self.service = service
        self.folder_id = folder_id
        self.filename = filename
        if content_type is None:
            content_type = (
                mimetypes.guess_type(filename)[0] or "application/octet-stream"
            )
        self.content_type = content_type
        if binary is None:
            binary = not content_type.startswith("text/")
        self.binary = binary
        self.overwrite_if_present = overwrite_if_present
        if self.binary:
            self.fh = io.BytesIO()
        else:
            self.fh = io.StringIO()
        self.fh.name = filename
        self.id = None

    def __enter__(self):
        return self.fh

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.overwrite_if_present:
                try:
                    most_recent_file = find_file_by_name(
                        self.service,
                        self.folder_id,
                        self.filename,
                        FindMode.MOST_RECENTLY_MODIFIED,
                    )
                    self.id = most_recent_file.id
                except NoMatchesError:
                    pass
            if self.id is not None:
                # overwrite the existing file
                file_metadata = {
                    "mimeType": self.content_type,
                }
                media = MediaIoBaseUpload(self.fh, mimetype=self.content_type)
                result = (
                    self.service.files()
                    .update(
                        body=file_metadata,
                        fileId=self.id,
                        media_body=media,
                        fields="id",
                    )
                    .execute(num_retries=NUM_RETRIES)
                )
                assert self.id == result["id"]

            else:
                file_metadata = {
                    "name": self.filename,
                    "parents": [self.folder_id],
                    "mimeType": self.content_type,
                }
                media = MediaIoBaseUpload(self.fh, mimetype=self.content_type)
                result = (
                    self.service.files()
                    .create(body=file_metadata, media_body=media, fields="id")
                    .execute(num_retries=NUM_RETRIES)
                )
                self.id = result["id"]
            self.fh.name = GDRIVE_ID_FORMAT_STRING.format(self.id)
            return False
        finally:
            self.fh.seek(0)


def mkdir(
    service: DriveService, parent_folder_id: str, folder_name: str
) -> DriveObject:
    """Creates a folder, given a parent_folder_id, and return the id."""
    file_metadata = {
        "name": folder_name,
        "mimeType": GDRIVE_FOLDER_MIMETYPE,
        "parents": [parent_folder_id],
    }
    result = (
        service.files()
        .create(body=file_metadata, fields="id")
        .execute(num_retries=NUM_RETRIES)
    )
    return DriveObject(
        drive_service=service,
        id=result["id"],
        name=folder_name,
        mimeType=GDRIVE_FOLDER_MIMETYPE,
    )


def mkdir_recursive(
    service: DriveService, parent_folder_id: str, path_components: List[str]
) -> str:
    """Attempts to recursively create all the path components starting at a parent_folder_id.  If a
    folder exists where we are trying to create one, we should use the existing one as much as
    possible, subject to race conditions.  Return the id of the most deeply nested folder.

    Logically, this is equivalent to POSIX `mkdir -p`
    """
    if len(path_components) == 0:
        return parent_folder_id

    next_folder_name = path_components[0]
    remaining_path_components = path_components[1:]

    results = [
        result
        for result in get_child_by_name(service, parent_folder_id, next_folder_name)
        if result.is_dir
    ]
    if len(results) > 1:
        raise MultipleMatchesError(
            f"folder has more than one child with name {next_folder_name}"
        )
    elif len(results) == 0:
        # create the folder
        next_folder_id = mkdir(service, parent_folder_id, next_folder_name).id
    else:
        assert len(results) == 1
        next_folder_id = results[0].id

    return mkdir_recursive(service, next_folder_id, remaining_path_components)


def get_layout_file_from_url(
    drive_service: DriveService, layout_file_url: str
) -> DriveObject:
    """Extracts the id parameter from a Google Drive URL and returns the file."""
    file_id = parse_qs(urlparse(layout_file_url).query)["id"][0]

    return find_file_by_id(drive_service, file_id)
