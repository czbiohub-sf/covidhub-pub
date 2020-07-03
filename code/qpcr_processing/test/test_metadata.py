import pytest

from qpcr_processing.conftest import (
    pcr_and_sample_barcode_for_rerun_only,
    pcr_and_sample_barcode_with_bravo_rna_entry,
)
from qpcr_processing.metadata import BravoMetadata


@pytest.mark.parametrize(
    "pcr_sample_barcode, expected_sample_barcode",
    [
        pcr_and_sample_barcode_for_rerun_only(),
        pcr_and_sample_barcode_with_bravo_rna_entry(),
    ],
)
@pytest.mark.integtest
def test_get_sample_barcode(
    google_sheets, pcr_sample_barcode, expected_sample_barcode,
):
    bravo_metadata = BravoMetadata.load_from_spreadsheet(
        pcr_sample_barcode, collective_form=google_sheets,
    )
    assert bravo_metadata.sample_barcode == expected_sample_barcode
