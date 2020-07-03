from dataclasses import dataclass
from typing import IO


@dataclass
class ChecksummedFileInfo:
    filename: str
    data: IO
    md5Checksum: str
