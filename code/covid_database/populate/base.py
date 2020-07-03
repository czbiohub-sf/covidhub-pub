import logging
from abc import abstractmethod
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO, StringIO
from threading import local
from typing import Dict, List, Optional, Sequence, Set

import pandas as pd
import yaml
from sqlalchemy.orm import Session
from tqdm import tqdm

import covidhub.google.drive as drive
from covid_database.types import ChecksummedFileInfo
from covidhub.collective_form import CollectiveForm
from covidhub.config import Config
from covidhub.google.utils import new_http_client_from_service


class BasePopulator:
    """
    Base abstract class for populating data in the DB

    Parameters
    ----------
    session :
        An open DB session object
    """

    def __init__(self, session: Session, **kwargs):
        self.session = session
        self.data = None

    @abstractmethod
    def initialize_data_from_source(self):
        """Initialize the data to use for population from a given source"""
        ...

    @abstractmethod
    def populate_models(self):
        """Create all models and insert into DB"""
        ...

    @property
    @abstractmethod
    def models_to_populate(self) -> List[str]:
        """The models that the Populator class will create and inset into the DB"""
        ...


class BaseWorksheetPopulator(BasePopulator):
    """
    Base class for a Populator that reads data from a dataframe.

    Parameters
    ----------
    session : Session
        An open DB session object
    dataframe : pd.DataFrame
        The dataframe that provides the data for this populator.
    """

    def __init__(self, session: Session, dataframe: pd.DataFrame):
        super().__init__(session)
        self.data = dataframe

    @property
    @abstractmethod
    def models_to_populate(self) -> List[str]:
        ...


class RemoteWorksheetPopulatorMixin:
    """
    Mixin class for a WorksheetPopulator that reads data from a specific google
    worksheet.

    Parameters
    ----------
    session : Session
        An open DB session object
    drive_service : DriveService
        An authenticated gdrive service object
    cfg : Config
        Config instance
    """

    def __init__(
        self, session: Session, drive_service: drive.DriveService, cfg: Config,
    ):
        super().__init__(session, self.initialize_data_from_source(drive_service, cfg))

    def initialize_data_from_source(
        self, drive_service: drive.DriveService, cfg: Config,
    ) -> pd.DataFrame:
        """Initialize the data to use for population from a given source"""
        file_id = cfg["DATA"][self.spreadsheet_id_config_key]
        logger = logging.getLogger(self.__class__.__module__)
        logger.info(f"Getting info from {self.sheet_name}")
        return pd.read_excel(
            BytesIO(
                drive_service.files()
                .export(fileId=file_id, mimeType=CollectiveForm.SHEET_MIMETYPE)
                .execute(num_retries=drive.NUM_RETRIES)
            ),
            sheet_name=self.sheet_name,
            skiprows=[1] if self.skip_header else None,
        )

    @property
    @abstractmethod
    def spreadsheet_id_config_key(self) -> str:
        ...

    @property
    @abstractmethod
    def sheet_name(self) -> str:
        ...

    @property
    def skip_header(self) -> bool:
        return False


class BaseLocalYamlPopulator(BasePopulator):
    """
    Base class for a Populator that reads data from a local Yaml file

    Parameters
    ----------
    session :
        An open DB session object
    path_to_file :
        Path to the local yaml file
    """

    def __init__(self, session: Session, path_to_file: str, **kwargs):
        super().__init__(session=session, **kwargs)
        self.path_to_file = path_to_file
        self.data = self.initialize_data_from_source()

    def initialize_data_from_source(self) -> Dict:
        """
        Initialize the Yaml data as a Dict
        """
        with open(self.path_to_file) as f:
            return yaml.full_load(f)

    @property
    @abstractmethod
    def models_to_populate(self) -> List[str]:
        ...


class BaseDriveFolderPopulator(BasePopulator):
    """
    Base class for a Populator that reads data from a specific drive folder

    Parameters
    ----------
    session :
        An open DB session object
    drive_service :
        An authenticated gdrive service object
    folder_path_components :
        The path components for the source folder
    """

    def __init__(
        self,
        session: Session,
        drive_service: drive.DriveService,
        folder_path_components: List[str] = None,
    ):
        super().__init__(session=session)
        self.session = session
        self.drive_service = drive_service
        self.folder_path_components = folder_path_components
        self.folder_id = drive.get_folder_id_of_path(
            self.drive_service, self.folder_path_components
        )
        self.data = self.initialize_data_from_source()

    def initialize_data_from_source(self) -> List[drive.DriveObject]:
        """
        Initialize the data as a list of file handlers from the drive folder
        """
        return drive.get_contents_by_folder_id(
            self.drive_service, self.folder_id, only_files=True
        )

    def load_files(
        self,
        file_ext: str = "",
        names: Optional[Set[str]] = None,
        checksums: Optional[Set[str]] = None,
    ) -> Sequence[ChecksummedFileInfo]:
        """Download all files from the source folder, using multithreaded downloads,
        and showing progress bar. Returns dictionary from name to contents in StringIO.

        Parameters
        ----------
        file_ext :
            Filter for selecting specific file extension
        names :
            Set of names that should be downloaded
        checksums :
            Set of md5Checksums that should *not* be downloaded
        """
        if checksums is None:
            checksums = set()

        # list of all the filenames we are fetching.
        if names is None:
            names = {
                drive_obj.name
                for drive_obj in self.data
                if drive_obj.name.endswith(file_ext)
                and drive_obj.md5Checksum not in checksums
            }

        # instantiate some thread-local storage for holding the HTTP clients.
        tls = local()

        def retrieve_file(filename: str) -> ChecksummedFileInfo:
            http_client = getattr(tls, "http", None)
            if http_client is None:
                http_client = new_http_client_from_service(self.drive_service)
                setattr(tls, "http", http_client)

            drive_obj = drive.find_file_by_name(
                self.drive_service,
                self.folder_id,
                filename,
                drive.FindMode.MOST_RECENTLY_MODIFIED,
                http=http_client,
            )

            with drive.get_file(
                self.drive_service, drive_obj.id, http=http_client
            ) as fh:
                data = fh.read()
                if isinstance(data, str):
                    data_fh = StringIO(data)
                elif isinstance(data, bytes):
                    data_fh = BytesIO(data)

                data_fh.name = filename  # needed for readers that expect a name attr
                return ChecksummedFileInfo(filename, data_fh, drive_obj.md5Checksum)

        with ThreadPoolExecutor() as tpe:
            # wrapping this in a list causes it to greedily download
            results = list(
                tqdm(
                    tpe.map(retrieve_file, names),
                    total=len(names),
                    # setting disable to None turns off the progress bar for the lambda
                    disable=None,
                )
            )

        return results

    @property
    @abstractmethod
    def models_to_populate(self):
        ...
