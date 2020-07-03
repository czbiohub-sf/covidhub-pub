import pytest

from covidhub.constants import ControlType
from covidhub.constants.enums import ControlsMappingType
from qpcr_processing.accession import parse_legacy_accession_data
from qpcr_processing.control_wells import (
    get_control_wells_from_type,
    update_accession_data_with_controls,
)


def test_custom_control_wells(legacy_plate_layout):

    accession_data = parse_legacy_accession_data(legacy_plate_layout)
    control_wells = get_control_wells_from_type(
        ControlsMappingType.Custom, accession_data
    )

    expected_mapping = {
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

    assert control_wells == expected_mapping


def test_standard_control_wells():

    control_wells = get_control_wells_from_type(
        controls_type=ControlsMappingType.Standard
    )

    expected_mapping = {
        "A1": ControlType.NTC,
        "A11": ControlType.NTC,
        "A12": ControlType.NTC,
        "H1": ControlType.NTC,
        "H11": ControlType.NTC,
        "H12": ControlType.NTC,
        "A8": ControlType.PC,
        "H8": ControlType.PC,
        "A9": ControlType.HRC,
        "H9": ControlType.HRC,
        "A10": ControlType.PBS,
        "H10": ControlType.PBS,
    }

    assert control_wells == expected_mapping


def test_validation_control_wells():

    control_wells = get_control_wells_from_type(
        controls_type=ControlsMappingType.Validation
    )

    expected_mapping = {
        "A1": ControlType.NTC,
        "B1": ControlType.NTC,
        "C1": ControlType.NTC,
        "D1": ControlType.NTC,
        "E1": ControlType.NTC,
        "F1": ControlType.NTC,
        "G1": ControlType.NTC,
        "H1": ControlType.NTC,
        "A12": ControlType.NTC,
        "B12": ControlType.NTC,
        "C12": ControlType.NTC,
        "D12": ControlType.NTC,
        "E12": ControlType.NTC,
        "F12": ControlType.NTC,
        "G12": ControlType.NTC,
        "H12": ControlType.NTC,
    }

    assert control_wells == expected_mapping


def control_wells_update_error(
    expected_hamilton_accession_data, standard_control_wells
):
    valid_accession_in_control = {"H9": "X47399"}
    accession_data = expected_hamilton_accession_data.update(valid_accession_in_control)
    with pytest.raises(ValueError) as excinfo:
        update_accession_data_with_controls(
            standard_control_wells, accession_data, "B123456"
        )
    assert "overwrites a valid accession" in str(excinfo.value)
