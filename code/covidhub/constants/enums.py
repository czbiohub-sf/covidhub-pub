from enum import Enum


class _strEnum(Enum):
    def __str__(self) -> str:
        return self.value


class Call(_strEnum):
    POS: str = "Pos"
    POS_REVIEW: str = "Positive, review required"
    POS_CLUSTER: str = "Review needed: Positive by cluster"
    POS_HOTWELL: str = "Review needed: Positive by hot well"
    NEG: str = "Neg"
    INV: str = "Inv"
    IND: str = "Ind"

    # calls for controls
    PASS: str = "Pass"
    FAIL: str = "Fail"

    # wording used for pos_cluster in V2
    V2_CLUSTER = "Possible cluster review needed"

    @property
    def short(self) -> str:
        if self.is_positive:
            return "Pos"
        else:
            return self.value

    @property
    def needs_review(self) -> str:
        if self.is_positive and self != Call.POS:
            return "Pos*"
        else:
            return self.short

    @property
    def is_positive(self) -> bool:
        return self in {Call.POS, Call.POS_REVIEW, Call.POS_CLUSTER, Call.POS_HOTWELL}

    @property
    def possible_cluster(self) -> bool:
        return self in {Call.POS_CLUSTER, Call.POS_HOTWELL}

    @property
    def rerun(self) -> bool:
        return self in {Call.POS_CLUSTER, Call.POS_HOTWELL, Call.INV, Call.IND}


class ControlType(_strEnum):
    NTC: str = "NTC"
    PC: str = "PC"
    PBS: str = "PBS"
    HRC: str = "HRC"

    @staticmethod
    def parse_control(accession: str):
        for control_type in (
            ControlType.NTC,
            ControlType.PC,
            ControlType.PBS,
            ControlType.HRC,
        ):
            if accession.startswith(control_type.value):
                return control_type

        return None


# different fluorophores
class Fluor(_strEnum):
    HEX: str = "HEX"
    FAM: str = "FAM"
    CY5: str = "Cy5"


# the mapping of four qpcr plate wells relative to a single sample plate well
class MappedWell(Enum):
    A1: str = "A1"
    A2: str = "A2"
    B1: str = "B1"
    B2: str = "B2"


class PlateMapType(_strEnum):
    LEGACY: str = "Legacy"
    WELLLIT: str = "WellLit"
    HAMILTON: str = "Hamilton"


class SamplePlateType(_strEnum):
    ORIGINAL: str = "Original Sample"  # the only type to report
    EXPERIMENTAL: str = "Experimental Plate"
    VALIDATION: str = "Validation Plate"


class ControlsMappingType(_strEnum):
    Standard = "Standard Controls"
    Validation = "LOD Controls"
    Custom = "Custom Controls"
    NoControls = "No Controls"
