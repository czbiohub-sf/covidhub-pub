import os
import re
from pathlib import Path
from typing import Optional

import yaml
from pkg_resources import resource_filename


def parse_config(config_path: Path, tag: str = "!ENV"):
    """
    Load a yaml configuration file and resolve any environment variables
    The environment variables must have !ENV before them and be in this format
    to be parsed: ${VAR_NAME}.

    Code adapted from Maria Karanasou:
    https://medium.com/swlh/python-yaml-configuration-with-environment-variables-parsing-77930f4273ac

    E.g.:

    database:
        host: !ENV ${HOST}
        port: !ENV ${PORT}
    app:
        log_path: !ENV '/var/${LOG_PATH}'
        something_else: !ENV '${AWESOME_ENV_VAR}/var/${A_SECOND_AWESOME_VAR}'

    :param config_path: the path to the yaml file
    :param tag: the tag to look for
    :return: the dict configuration
    """
    # pattern for global vars: look for ${word}
    pattern = re.compile(r".*?\${(\w+)}.*?")
    loader = yaml.SafeLoader

    # the tag will be used to mark where to start searching for the pattern
    # e.g. somekey: !ENV somestring${MYENVVAR}blah blah blah
    loader.add_implicit_resolver(tag, pattern, None)

    def constructor_env_variables(loader, node):
        """
        Extracts the environment variable from the node's value
        :param yaml.Loader loader: the yaml loader
        :param node: the current node in the yaml
        :return: the parsed string that contains the value of the environment
        variable
        """
        value = loader.construct_scalar(node)
        match = pattern.findall(value)  # to find all env variables in line
        if match:
            full_value = value
            for g in match:
                full_value = full_value.replace(f"${{{g}}}", os.environ.get(g, ""))
            return full_value
        return value

    loader.add_constructor(tag, constructor_env_variables)

    with config_path.open("r") as conf_data:
        return yaml.load(conf_data, Loader=loader)


class Config(dict):
    UNDEFINED_ENV = "undefined env"

    def __init__(self, extra_config: Optional[Path] = None):
        super(Config, self).__init__()

        config_path = Path(resource_filename("covidhub", "config.yaml"))

        self.update(parse_config(config_path))
        if extra_config is not None:
            self.update(parse_config(extra_config))

        self.post_load_hook()

    def post_load_hook(self):
        """Hook that implementations can override to alter the configuration after the
        config files are loaded"""
        ...

    @property
    def INPUT_GDRIVE_PATH(self):
        return self["DATA"]["input_drive_path"].split("/")

    @property
    def OUTPUT_GDRIVE_PATH(self):
        return self["DATA"]["output_drive_path"].split("/")

    @property
    def PCR_LOGS_FOLDER(self):
        """this is where the PCR logs are written to by the PCR machines."""
        return self.INPUT_GDRIVE_PATH + self["DATA"]["pcr_logs_folder"]

    @property
    def PLATE_LAYOUT_FOLDER(self):
        """location on google drive where plate maps are uploaded."""
        return self.INPUT_GDRIVE_PATH + self["DATA"]["plate_layout_folder"]

    @property
    def LAYOUT_PDF_FOLDER(self):
        """location on google drive where plate map PDFs are uploaded."""
        return self.INPUT_GDRIVE_PATH + self["DATA"]["plate_layout_pdf_folder"]

    @property
    def CHINA_BASIN_CSV_REPORTS_FOLDER(self):
        """this is where the bio rad formatted results of the pipeline are written to."""
        return self.OUTPUT_GDRIVE_PATH + self["DATA"]["china_basin_csv_reports_folder"]

    @property
    def CSV_RESULTS_FOLDER(self):
        """this is where the results of the pipeline are written to."""
        return self.OUTPUT_GDRIVE_PATH + self["DATA"]["csv_reports_folder"]

    @property
    def CSV_RESULTS_FOLDER_TRACKING(self):
        """this is where we should read csv results for accession tracking"""
        return self.INPUT_GDRIVE_PATH + self["DATA"]["csv_reports_folder"]

    @property
    def FINAL_REPORTS_FOLDER(self):
        """where to save the PDF and csv results"""
        return self.OUTPUT_GDRIVE_PATH + self["DATA"]["final_reports_folder"]

    @property
    def PCR_MARKERS_FOLDER(self):
        """this is where we save the markers for the barcodes we've processed."""
        return self.OUTPUT_GDRIVE_PATH + self["DATA"]["pcr_markers_folder"]

    @property
    def PCR_MARKERS_FOLDER_TRACKING(self):
        """this is where we should read he markers for the barcodes we've processed for tracking"""
        return self.INPUT_GDRIVE_PATH + self["DATA"]["pcr_markers_folder"]

    @property
    def ACCESSSION_TRACKING_MARKERS_FOLDER(self):
        """this is where we should read he markers for the barcodes we've processed for tracking"""
        return (
            self.OUTPUT_GDRIVE_PATH + self["DATA"]["accession_tracking_markers_folder"]
        )

    @property
    def ACCESSION_LOCATIONS_FOLDER(self):
        return self.INPUT_GDRIVE_PATH + self["DATA"]["accession_locations_folder"]

    @property
    def aws_env(self):
        return os.environ.get("ENV", Config.UNDEFINED_ENV)


class AlternateGDriveConfig(Config):
    """An implementation of Config that overrides the input drive path and the output
    drive path."""

    def __init__(self, gdrive_path):
        self.base_folder_name = gdrive_path
        super().__init__()

    def post_load_hook(self):
        # override the input_drive_path
        self["DATA"]["input_drive_path"] = self.base_folder_name
        self["DATA"]["output_drive_path"] = self.base_folder_name


def get_git_info():
    """
    Log Git info from a custom GIT_HEAD file.
    Example GIT_HEAD: 8055a32 master v1.0
    """
    output = ""
    filename = Path(resource_filename("qpcr_processing", "GIT_HEAD"))
    if filename.is_file():
        try:
            with filename.open("r") as f:
                output = f.read()
        except Exception as err:
            print(f"Couldn't read from {filename}: {err}")
    else:
        print(f"{filename} not found")
    return output
