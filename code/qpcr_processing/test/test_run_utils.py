import pytest

from qpcr_processing.run_files import RunFiles


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (
            "logs/D041758_All Wells - Run Information.csv",
            ("D041758", RunFiles.RUN_INFO, None),
        ),
        (
            "D041758_All Wells - Quantification Cq Results.csv",
            ("D041758", RunFiles.QUANT_CQ, None),
        ),
        ("B131267 -   Run Information.csv", ("B131267", RunFiles.RUN_INFO, None)),
        (
            "B131267 - Quantification Amplification Results_HEX.csv",
            ("B131267", RunFiles.QUANT_AMP, "HEX"),
        ),
        (
            "B131267 - Quantification Amplification Results_FAM.csv",
            ("B131267", RunFiles.QUANT_AMP, "FAM"),
        ),
        (
            "B131267 - Quantification Amplification Results_Cy5.csv",
            ("B131267", RunFiles.QUANT_AMP, "Cy5"),
        ),
        (
            "lots/of/folders/B131267073149164483073149164483 - Run Information.csv",
            ("B131267073149164483073149164483", RunFiles.RUN_INFO, None),
        ),
    ],
)
def test_get_qpcr_file_type(test_input, expected):
    m = RunFiles.get_qpcr_file_type(test_input)
    assert (m["BARCODE"], m["FILE_TYPE"], m["FLUOR"]) == expected


@pytest.mark.parametrize(
    "test_input",
    [
        "b123131 - Bad Barcode.csv",
        "no barcode - Run Information.csv" "B123112__Nonstandard-Format.csv",
        "B123134 - W3ird Ch@racters_HAX.csv",
        "/actually/a/folder/D041758_All Wells - Run Information.csv/",
        "B1231241 - No extension",
    ],
)
def test_bad_file_names(test_input):
    assert RunFiles.get_qpcr_file_type(test_input) is None
