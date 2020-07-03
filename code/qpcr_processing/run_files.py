import os
import re
from pathlib import Path
from typing import Match, Optional, Union

from covidhub.constants import Fluor
from covidhub.google.drive import DriveObject


class RunFiles:
    # the three type of files we need for processing
    RUN_INFO: str = "Run Information"
    QUANT_CQ: str = "Quantification Cq Results"
    QUANT_AMP: str = "Quantification Amplification Results"

    # symbolic names for get_qpcr_file_type regex
    BARCODE: str = "BARCODE"
    FILE_TYPE: str = "FILE_TYPE"
    FLUOR: str = "FLUOR"

    def __init__(self, run_info=None, quant_cq=None, quant_amp=None):
        self.run_info = run_info
        self.quant_cq = quant_cq
        self.quant_amp = quant_amp or dict()

    def add_file(self, m: Match, entry: Union[Path, DriveObject]):
        """Given a match object from get_qpcr_file_type, add the file to this set,
        or ignore it if it's not one we're looking for."""
        file_type = m[RunFiles.FILE_TYPE]

        if file_type == RunFiles.RUN_INFO:
            self.run_info = entry
        elif file_type == RunFiles.QUANT_CQ:
            self.quant_cq = entry
        elif file_type == RunFiles.QUANT_AMP:
            self.quant_amp[Fluor(m[RunFiles.FLUOR])] = entry

    @property
    def all_files(self):
        return all((self.run_info, self.quant_cq, self.quant_amp))

    @staticmethod
    def get_qpcr_file_type(filename: str) -> Optional[Match]:
        """
        regular expression for matching files of the form
            {barcode}{optional stuff like `_All Wells `}- +{file type}[_{fluor}].csv
        takes the basename of a qpcr output file and returns a match object (or None)
        with barcode, file_type and optional fluor values
        """

        return re.match(
            r"^(?P<BARCODE>[A-Z0-9]+).*-\s*"
            r"(?P<FILE_TYPE>[a-zA-Z ]+)"
            r"(?:_(?P<FLUOR>[a-zA-Z0-9]+))?\.csv$",
            os.path.basename(filename),
        )
