import pytest

from covidhub.constants import Call, ControlType
from qpcr_processing.protocol import SOP_V2, SOP_V3


@pytest.mark.parametrize(
    "values, expected_call",
    [
        ({"N": "NaN", "E": "NaN", "RNAse P": "NaN"}, Call.INV),
        ({"N": "NaN", "E": "NaN", "RNAse P": 39.0}, Call.INV),
        ({"N": "NaN", "E": "NaN", "RNAse P": 35.4}, Call.NEG),
        ({"N": "NaN", "E": 42.1, "RNAse P": 35.4}, Call.IND),
        ({"N": "NaN", "E": 42.1, "RNAse P": "NaN"}, Call.IND),
        ({"N": 20.0, "E": "NaN", "RNAse P": "NaN"}, Call.IND),
        ({"N": 20.0, "E": 42.1, "RNAse P": "NaN"}, Call.IND),
        ({"N": 20.0, "E": 42.1, "RNAse P": 36.0}, Call.IND),
        ({"N": 41.4, "E": 42.1, "RNAse P": "NaN"}, Call.IND),
        ({"N": 41.4, "E": 42.1, "RNAse P": 38.0}, Call.IND),
        ({"N": 31.4, "E": 32.1, "RNAse P": "NaN"}, Call.POS),
        ({"N": 31.4, "E": 39.9, "RNAse P": 33.4}, Call.POS),
        ({"N": 31.4, "E": 32.1, "RNAse P": 42.4}, Call.POS),
    ],
)
def test_well_calling_v2(values, expected_call):
    """Test calling logic for SOP-V2 for a variety of measurements."""
    call = SOP_V2.call_well(values)
    assert call == expected_call


@pytest.mark.parametrize(
    "values, expected_call",
    [
        ({"N": "NaN", "E": "NaN", "RNAse P": "NaN"}, Call.INV),
        ({"N": "NaN", "E": "NaN", "RNAse P": 44.9}, Call.NEG),
        ({"N": "NaN", "E": 42.1, "RNAse P": 35.4}, Call.POS_REVIEW),
        ({"N": "NaN", "E": 42.1, "RNAse P": "NaN"}, Call.POS_REVIEW),
        ({"N": 20.0, "E": "NaN", "RNAse P": "NaN"}, Call.POS_REVIEW),
        ({"N": 20.0, "E": 42.1, "RNAse P": "NaN"}, Call.POS_REVIEW),
        ({"N": 20.0, "E": 42.1, "RNAse P": 36.0}, Call.POS_REVIEW),
        ({"N": 41.4, "E": 42.1, "RNAse P": "NaN"}, Call.POS_REVIEW),
        ({"N": 41.4, "E": 42.1, "RNAse P": 38.0}, Call.POS_REVIEW),
        ({"N": 31.4, "E": 32.1, "RNAse P": "NaN"}, Call.POS),
        ({"N": 31.4, "E": 39.9, "RNAse P": 33.4}, Call.POS),
        ({"N": 31.4, "E": 32.1, "RNAse P": 42.4}, Call.POS),
    ],
)
def test_well_calling_v3(values, expected_call):
    """Test calling logic for SOP-V3 for a variety of measurements."""
    call = SOP_V3.call_well(values)
    assert call == expected_call


@pytest.mark.parametrize("protocol", (SOP_V2, SOP_V3))
@pytest.mark.parametrize(
    "control_type, values, expected_call",
    [
        (ControlType.NTC, {"N": "NaN", "E": "NaN", "RNAse P": "NaN"}, Call.PASS),
        (ControlType.NTC, {"N": "NaN", "E": "NaN", "RNAse P": 38.0}, Call.FAIL),
        (ControlType.NTC, {"N": 45.2, "E": "NaN", "RNAse P": "NaN"}, Call.FAIL),
        (ControlType.PBS, {"N": "NaN", "E": "NaN", "RNAse P": "NaN"}, Call.PASS),
        (ControlType.PBS, {"N": 40.2, "E": "NaN", "RNAse P": "NaN"}, Call.FAIL),
        (ControlType.PC, {"N": 30.1, "E": 31.1, "RNAse P": 32.0}, Call.PASS),
        (ControlType.PC, {"N": 30.1, "E": 29.9, "RNAse P": 38.0}, Call.FAIL),
        (ControlType.PC, {"N": 38.1, "E": 29.9, "RNAse P": 38.0}, Call.FAIL),
        (ControlType.PC, {"N": "NaN", "E": 29.9, "RNAse P": 32.0}, Call.FAIL),
        (ControlType.HRC, {"N": "NaN", "E": "NaN", "RNAse P": 29.0}, Call.PASS),
        (ControlType.HRC, {"N": "NaN", "E": 29.9, "RNAse P": 32.0}, Call.FAIL),
        (ControlType.HRC, {"N": "NaN", "E": "NaN", "RNAse P": 39.0}, Call.FAIL),
        (ControlType.HRC, {"N": "NaN", "E": 42.0, "RNAse P": 39.0}, Call.FAIL),
        (ControlType.HRC, {"N": 43.1, "E": "NaN", "RNAse P": "NaN"}, Call.FAIL),
    ],
)
def test_control_calling(protocol, control_type, values, expected_call):
    """Test control logic for SOP-V2 and V3 for a variety of measurements."""
    call = protocol.check_control(values, control_type)
    assert call == expected_call
