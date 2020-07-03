import numpy as np
import pytest

from covidhub.constants import Call, ControlType
from qpcr_processing.protocol import SOP_V2, SOP_V3
from qpcr_processing.well_results import WellResults


@pytest.mark.parametrize(
    "protocol, values, expected_call",
    [
        (
            SOP_V2,
            {
                "A1": WellResults(
                    gene_cts={"N": np.nan, "E": np.nan, "RNAse P": np.nan},
                    call=Call.PASS,
                    control_type=ControlType.NTC,
                ),
                "A2": WellResults(
                    gene_cts={"N": 32, "E": 21, "RNAse P": 35}, call=Call.POS
                ),
                "A3": WellResults(
                    gene_cts={"N": np.nan, "E": np.nan, "RNAse P": 22}, call=Call.NEG
                ),
                "B1": WellResults(
                    gene_cts={"N": 22, "E": 35, "RNAse P": np.nan}, call=Call.POS
                ),
                "B2": WellResults(
                    gene_cts={"N": 37, "E": 5, "RNAse P": np.nan}, call=Call.POS
                ),
                "B3": WellResults(
                    gene_cts={"N": 12, "E": 7, "RNAse P": 35}, call=Call.POS
                ),
                "C1": WellResults(
                    gene_cts={"N": 35, "E": 14, "RNAse P": np.nan}, call=Call.POS
                ),
                "C2": WellResults(
                    gene_cts={"N": 6, "E": 44, "RNAse P": np.nan}, call=Call.IND
                ),
                "C3": WellResults(
                    gene_cts={"N": 33, "E": 32, "RNAse P": np.nan}, call=Call.POS
                ),
            },
            {"A2", "B2", "C3"},
        ),
        (
            SOP_V3,
            {
                "A1": WellResults(
                    gene_cts={"N": np.nan, "E": np.nan, "RNAse P": np.nan},
                    call=Call.PASS,
                    control_type=ControlType.NTC,
                ),
                "A2": WellResults(
                    gene_cts={"N": 32, "E": 21, "RNAse P": 35}, call=Call.POS
                ),
                "A3": WellResults(
                    gene_cts={"N": np.nan, "E": np.nan, "RNAse P": 22}, call=Call.NEG
                ),
                "B1": WellResults(
                    gene_cts={"N": 22, "E": 35, "RNAse P": np.nan}, call=Call.POS
                ),
                "B2": WellResults(
                    gene_cts={"N": 37, "E": 5, "RNAse P": np.nan}, call=Call.POS
                ),
                "B3": WellResults(
                    gene_cts={"N": 12, "E": 7, "RNAse P": 35}, call=Call.POS
                ),
                "C1": WellResults(
                    gene_cts={"N": 35, "E": 14, "RNAse P": np.nan}, call=Call.POS
                ),
                "C2": WellResults(
                    gene_cts={"N": 6, "E": 44, "RNAse P": np.nan}, call=Call.POS_REVIEW
                ),
                "C3": WellResults(
                    gene_cts={"N": 33, "E": 32, "RNAse P": np.nan}, call=Call.POS
                ),
            },
            {"A2", "B1", "B2", "C1", "C2", "C3"},
        ),
    ],
)
def test_get_wells_positive_by_cluster(protocol, values, expected_call):
    protocol.flag_contamination(values)
    wells_to_rerun = {
        well_id
        for well_id, results in values.items()
        if results.call == Call.POS_CLUSTER
    }
    assert wells_to_rerun == expected_call


@pytest.mark.parametrize(
    "values, expected_call",
    [
        (
            {
                "A2": WellResults(
                    gene_cts={"N": 38, "E": 39, "RNAse P": 40}, call=Call.POS,
                ),
                "D2": WellResults(
                    gene_cts={"N": 8, "E": np.nan, "RNAse P": 40}, call=Call.POS_REVIEW
                ),
                "D3": WellResults(
                    gene_cts={"N": 20, "E": 20, "RNAse P": np.nan}, call=Call.POS
                ),
                "B4": WellResults(
                    gene_cts={"N": np.nan, "E": 45, "RNAse P": 29}, call=Call.POS_REVIEW
                ),
                "C4": WellResults(
                    gene_cts={"N": 31, "E": 29, "RNAse P": 40}, call=Call.POS
                ),
                "D4": WellResults(
                    gene_cts={"N": 16, "E": 20, "RNAse P": 29}, call=Call.POS
                ),
                "F4": WellResults(
                    gene_cts={"N": 31, "E": 33, "RNAse P": 20}, call=Call.POS
                ),
                "D9": WellResults(
                    gene_cts={"N": 45, "E": 45, "RNAse P": 20}, call=Call.POS_REVIEW
                ),
            },
            {"A2", "C4", "F4"},
        ),
    ],
)
def test_get_wells_positive_by_hot_well(values, expected_call):
    SOP_V3.flag_contamination(values)
    wells_to_rerun = {
        well_id
        for well_id, results in values.items()
        if results.call == Call.POS_HOTWELL
    }
    assert wells_to_rerun == expected_call
