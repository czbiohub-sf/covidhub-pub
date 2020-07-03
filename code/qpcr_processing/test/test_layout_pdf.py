import subprocess

import pytest


@pytest.mark.integtest
@pytest.mark.parametrize("barcode", ["SP000001", "SP000210", "SP000228"])
def test_make_layout_pdf_cli(tmp_path, barcode):
    args = [
        "make_layout_pdf",
        "--secret-id",
        "covid-19/google_test_creds",
        "--output-dir",
        tmp_path,
        barcode,
    ]

    subprocess.check_call(args)

    assert (tmp_path / f"{barcode}.pdf").exists()
