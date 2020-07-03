import csv
import subprocess
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).parent.parent.parent.parent
EXAMPLE_FILE_DIR = PROJECT_DIR / "example_files"

ACCESSION_TRACKING_OUTPUT = EXAMPLE_FILE_DIR / "Testing Accession Tracking.csv"
CLIN_LAB_REPORTING_OUTPUT = EXAMPLE_FILE_DIR / "Testing Clin Lab Reporting.csv"
SUPERVISOR_PLATE_QUEUE_OUTPUT = EXAMPLE_FILE_DIR / "Supervisor Plate Queue Testing.csv"
ACCESSION_TRACKING_TO_COMPARE = (
    EXAMPLE_FILE_DIR / "testing_accession_tracking_for_comparison.csv"
)
CLIN_LAB_REPORTING_TO_COMPARE = (
    EXAMPLE_FILE_DIR / "testing_clin_lab_reporting_for_comparison.csv"
)
SUPERVISOR_PLATE_QUEUE_TO_COMPARE = (
    EXAMPLE_FILE_DIR / "supervisor_plate_queue_testing_for_comparison.csv"
)

OUTPUT_FILES = [
    ACCESSION_TRACKING_OUTPUT,
    CLIN_LAB_REPORTING_OUTPUT,
    SUPERVISOR_PLATE_QUEUE_OUTPUT,
]
COMPARISON_FILES = [
    ACCESSION_TRACKING_TO_COMPARE,
    CLIN_LAB_REPORTING_TO_COMPARE,
    SUPERVISOR_PLATE_QUEUE_TO_COMPARE,
]


@pytest.mark.accession
def test_accession_tracking():
    """
    Run  accession tracking with 4 sample barcodes [SP000147 SP000150 SP000136 SP000226]
    and verify the results match our saved records.
    """

    subprocess.run(
        "make test-compile-accessions-local", shell=True, check=True, cwd=PROJECT_DIR
    )
    for output_file in OUTPUT_FILES:
        assert output_file.exists()

    for output_file, comparison_file in zip(OUTPUT_FILES, COMPARISON_FILES):
        try:
            with output_file.open("r") as t1, comparison_file.open("r") as t2:
                rdr1 = csv.reader(t1)
                rdr2 = csv.reader(t2)
                for row1, row2, in zip(rdr1, rdr2):
                    assert row1 == row2
        finally:
            output_file.unlink()
