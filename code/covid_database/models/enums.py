import string
from enum import Enum
from itertools import product

from covidhub.constants.enums import (  # noqa: F401
    Call,
    ControlType,
    Fluor,
    MappedWell,
    PlateMapType,
    SamplePlateType,
)

# Enum for valid 96-well-plate wells
WellId96 = Enum(
    "WellId96",
    [f"{row}{col}" for row, col in product(string.ascii_uppercase[:8], range(1, 13))],
)

# Enum for valid 384-well-plate wells
WellId384 = Enum(
    "WellId384",
    [f"{row}{col}" for row, col in product(string.ascii_uppercase[:16], range(1, 25))],
)


class Protocol(Enum):
    SOP_V1: str = "SOP-V1"
    SOP_V2: str = "SOP-V2"
    UDGprotocol: str = "UDGprotocol"
    SOP_V3: str = "SOP-V3"


class PlateType(Enum):
    SAMPLE: str = "Sample Plate"
    RNA: str = "RNA plate"
    QPCR: str = "qPCR plate"
    REAGENT: str = "Reagent Plate"


# different types of reagent plates that are prepared
class ReagentPlateType(Enum):
    RPW1: str = "RPW1"  # wash buffer 1
    RPW2: str = "RPW2"  # wash buffer 2
    RPET: str = "RPET"  # ethanol 1-4
    RPD1: str = "RPD1"  # dnase I
    RPRPB: str = "RPRPB"  # RNA prep buffer
    RPH2O: str = "RPH2O"  # water
    RPMB: str = "RPMB"  # magbeads
    RPVB: str = "RPVB"  # viral DNA/RNA buffer
    RPPK: str = "RPPK"  # proteinase K
    RPPB: str = "RPPB"  # pathogen DNA/RNA buffer (deprecated)


# class for different types of waste
class WasteType(Enum):
    BAGS: str = "Solid Waste"
    BOTTLES: str = "Liquid Waste"
    PLATES: str = "Plates"


# Laboratory Locations, currently used for where sample plates were prepared
class LabLocation(Enum):
    CHINA_BASIN: str = "China Basin"
    BIOHUB: str = "Biohub"


# the eight blocks in a freezer rack
FreezerBlock = Enum(
    "FreezerBlock", [f"{level}{block}" for level in ("A", "B") for block in range(1, 8)]
)


class ContractStatus(Enum):
    YES: str = "Yes"
    PENDING: str = "Pending"
    NO: str = "No"
    NotApplicable: str = "Not Applicable"


class NGSProjectType(Enum):
    INTERNAL: str = "Internal"
    DPH: str = "DPH"
    OTHER: str = "Other"
