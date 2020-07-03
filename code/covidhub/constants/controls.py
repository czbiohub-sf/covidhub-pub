from covidhub.constants.enums import ControlType

CONTROL_NAMES = {
    "Water_1": ControlType.NTC,
    "Water_2": ControlType.NTC,
    "Water_3": ControlType.NTC,
    "Water_4": ControlType.NTC,
    "Water_5": ControlType.NTC,
    "Water_6": ControlType.NTC,
    "Water": ControlType.NTC,
    "water": ControlType.NTC,
    "PC": ControlType.PC,
    "HSC": ControlType.HRC,
    "UTM": ControlType.PBS,
    "PC_1": ControlType.PC,
    "PC_2": ControlType.PC,
    "HSC_1": ControlType.HRC,
    "HSC_2": ControlType.HRC,
    "UTM_1": ControlType.PBS,
    "UTM_2": ControlType.PBS,
    "NTC": ControlType.NTC,
    "NC": ControlType.NTC,
    "HRC": ControlType.HRC,
    "PBS": ControlType.PBS,
}


VALIDATION_CONTROL_WELLS = {
    "A1": ControlType.NTC,
    "A12": ControlType.NTC,
    "B1": ControlType.NTC,
    "B12": ControlType.NTC,
    "C1": ControlType.NTC,
    "C12": ControlType.NTC,
    "D1": ControlType.NTC,
    "D12": ControlType.NTC,
    "E1": ControlType.NTC,
    "E12": ControlType.NTC,
    "F1": ControlType.NTC,
    "F12": ControlType.NTC,
    "G1": ControlType.NTC,
    "G12": ControlType.NTC,
    "H1": ControlType.NTC,
    "H12": ControlType.NTC,
}


STANDARD_CONTROL_WELLS = {
    "A1": ControlType.NTC,
    "A8": ControlType.PC,
    "A9": ControlType.HRC,
    "A10": ControlType.PBS,
    "A11": ControlType.NTC,
    "A12": ControlType.NTC,
    "H1": ControlType.NTC,
    "H8": ControlType.PC,
    "H9": ControlType.HRC,
    "H10": ControlType.PBS,
    "H11": ControlType.NTC,
    "H12": ControlType.NTC,
}
