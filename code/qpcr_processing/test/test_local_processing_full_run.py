import csv
import shutil
import subprocess
from pathlib import Path
from typing import Sequence

import pytest

from covidhub.constants import PlateMapType
from qpcr_processing.run_files import RunFiles


class RunSet:
    """A RunSet describes all the data needed to invoke a local processing run,
    including the names of the files we get the input data from and the names of the
    files we save the input data from.  It is flexible such that we can rename input
    files before we invoke local processing.  If this flexibility is not needed, use
    NormalRunSet, which does not rename files."""

    def __init__(
        self,
        barcode: str,
        sop: str,
        *,
        runinfo_dst_filename: str,
        runinfo_src_filename: str,
        quant_cq_dst_filename: str,
        quant_cq_src_filename: str,
        amp_dst_filenames: Sequence[str],
        amp_src_filenames: Sequence[str],
        plate_map_type: PlateMapType,
        plate_map_dst_file: str,
        plate_map_src_file: str,
        generated_output_filename: str,
        reference_output_filename: str,
        existence_output_filenames: Sequence[str],
    ):
        self.barcode = barcode
        self.sop = sop
        self.runinfo_dst_filename = runinfo_dst_filename
        self.runinfo_src_filename = runinfo_src_filename
        self.quant_cq_dst_filename = quant_cq_dst_filename
        self.quant_cq_src_filename = quant_cq_src_filename
        self.amp_dst_filenames = amp_dst_filenames
        self.amp_src_filenames = amp_src_filenames
        self.plate_map_type = plate_map_type
        self.plate_map_dst_filename = plate_map_dst_file
        self.plate_map_src_filename = plate_map_src_file
        self.generated_output_filename = generated_output_filename
        self.reference_output_filename = reference_output_filename
        self.existence_output_filenames = existence_output_filenames

    def setup(self, src_path: Path, dst_path: Path):
        input_filenames = [
            self.runinfo_src_filename,
            self.quant_cq_src_filename,
            self.plate_map_src_filename,
        ]

        input_filenames.extend(self.amp_src_filenames)

        output_filenames = [
            self.runinfo_dst_filename,
            self.quant_cq_dst_filename,
            self.plate_map_dst_filename,
        ]

        output_filenames.extend(self.amp_dst_filenames)

        for input_filename, output_filename in zip(input_filenames, output_filenames):
            shutil.copy(src_path / input_filename, dst_path / output_filename)

    def as_runfiles(self):
        run_files = RunFiles(self.runinfo_dst_filename, self.quant_cq_dst_filename)

        for amp_file in self.amp_dst_filenames:
            run_files.add_file(RunFiles.get_qpcr_file_type(amp_file), Path(amp_file))

        return run_files


class NormalRunSet(RunSet):
    def __init__(
        self,
        barcode: str,
        sop: str,
        runinfo_filename: str,
        quant_cq_filename: str,
        amp_filenames: Sequence[str],
        generated_output_filename: str,
        reference_output_filename: str,
        existence_output_filenames: Sequence[str],
        plate_map_type: PlateMapType,
        plate_map_filename: str,
    ):
        super().__init__(
            barcode,
            sop,
            runinfo_dst_filename=runinfo_filename,
            runinfo_src_filename=runinfo_filename,
            quant_cq_dst_filename=quant_cq_filename,
            quant_cq_src_filename=quant_cq_filename,
            amp_dst_filenames=amp_filenames,
            amp_src_filenames=amp_filenames,
            plate_map_type=plate_map_type,
            plate_map_dst_file=plate_map_filename,
            plate_map_src_file=plate_map_filename,
            generated_output_filename=generated_output_filename,
            reference_output_filename=reference_output_filename,
            existence_output_filenames=existence_output_filenames,
        )


PROJECT_DIR = Path(__file__).parent.parent.parent.parent
EXAMPLE_FILE_DIR = PROJECT_DIR / "example_files"

# V1 dataset.
SP000001_D041758 = NormalRunSet(
    barcode="D041758",
    sop="SOP-V1",
    runinfo_filename="D041758_All Wells - Run Information.csv",
    quant_cq_filename="D041758_All Wells -  Quantification Cq Results.csv",
    amp_filenames=(
        "D041758_All Wells -  Quantification Amplification Results_FAM.csv",
    ),
    plate_map_type=PlateMapType.WELLLIT,
    plate_map_filename="20200319-174657_SP000001_tube_to_plate.csv",
    generated_output_filename="SP000001-D041758_cb_results.csv",
    reference_output_filename="SP000001-D041758_cb_results-for-comparison.csv",
    existence_output_filenames=("SP000001-D041758_final.pdf",),
)

# V1 dataset.
SP000002_D041761 = NormalRunSet(
    barcode="D041761",
    sop="SOP-V1",
    runinfo_filename="D041761_All Wells - Run Information.csv",
    quant_cq_filename="D041761_All Wells -  Quantification Cq Results.csv",
    amp_filenames=(
        "D041761_All Wells -  Quantification Amplification Results_FAM.csv",
        "D041761_All Wells -  Quantification Amplification Results_HEX.csv",
    ),
    plate_map_type=PlateMapType.LEGACY,
    plate_map_filename="96sample_plate_accessions_SP000002.xlsx",
    generated_output_filename="SP000002-D041761_cb_results.csv",
    reference_output_filename="SP000002-D041761_cb_results-for-comparison.csv",
    existence_output_filenames=("SP000002-D041761_final.pdf",),
)

# V2 dataset missing one of the fluors
SP000114_B132312_no_HEX = NormalRunSet(
    barcode="B132312",
    sop="SOP-V2",
    runinfo_filename="B132312_All Wells - Run Information.csv",
    quant_cq_filename="B132312_All Wells -  Quantification Cq Results.csv",
    amp_filenames=(
        "B132312_All Wells -  Quantification Amplification Results_FAM.csv",
    ),
    plate_map_type=PlateMapType.HAMILTON,
    plate_map_filename="04082020-173053_SP000114_hamilton.csv",
    generated_output_filename="SP000114-B132312_cb_results.csv",
    reference_output_filename="SP000114-B132312_cb_results-for-comparison.csv",
    existence_output_filenames=("SP000114-B132312_final.pdf",),
)

# Hamilton dataset
SP000114_B132312 = NormalRunSet(
    barcode="B132312",
    sop="SOP-V2",
    runinfo_filename="B132312_All Wells - Run Information.csv",
    quant_cq_filename="B132312_All Wells -  Quantification Cq Results.csv",
    amp_filenames=(
        "B132312_All Wells -  Quantification Amplification Results_FAM.csv",
        "B132312_All Wells -  Quantification Amplification Results_HEX.csv",
    ),
    plate_map_type=PlateMapType.HAMILTON,
    plate_map_filename="04082020-173053_SP000114_hamilton.csv",
    generated_output_filename="SP000114-B132312_cb_results.csv",
    reference_output_filename="SP000114-B132312_cb_results-for-comparison.csv",
    existence_output_filenames=("SP000114-B132312_final.pdf",),
)

SP000114_B132312_bad_plate_map = NormalRunSet(
    barcode="B132312",
    sop="SOP-V2",
    runinfo_filename="B132312_All Wells - Run Information.csv",
    quant_cq_filename="B132312_All Wells -  Quantification Cq Results.csv",
    amp_filenames=(
        "B132312_All Wells -  Quantification Amplification Results_FAM.csv",
        "B132312_All Wells -  Quantification Amplification Results_HEX.csv",
    ),
    plate_map_type=PlateMapType.HAMILTON,
    plate_map_filename="04082020-173053_SP000114_hamilton_bad_columns.csv",
    generated_output_filename="SP000114-B132312_cb_results.csv",
    reference_output_filename="SP000114-B132312_cb_results-for-comparison.csv",
    existence_output_filenames=("SP000114-B132312_final.pdf",),
)

# Custom Controls
SP000214_B131885 = NormalRunSet(
    barcode="B131885",
    sop="SOP-V2",
    runinfo_filename="B131885_All Wells - Run Information.csv",
    quant_cq_filename="B131885_All Wells -  Quantification Cq Results.csv",
    amp_filenames=(
        "B131885_All Wells -  Quantification Amplification Results_HEX.csv",
        "B131885_All Wells -  Quantification Amplification Results_FAM.csv",
    ),
    plate_map_type=PlateMapType.LEGACY,
    plate_map_filename="96sample_plate_accessions_SP000214.xlsx",
    generated_output_filename="SP000214-B131885_cb_results.csv",
    reference_output_filename="SP000214-B131885_cb_results-for-comparison.csv",
    existence_output_filenames=("SP000214-B131885_final.pdf",),
)


# Full clinical plate, including a cluster of positives
SP000151_B131289 = NormalRunSet(
    barcode="B131289",
    sop="SOP-V2",
    runinfo_filename="B131289_All Wells - Run Information.csv",
    quant_cq_filename="B131289_All Wells -  Quantification Cq Results.csv",
    amp_filenames=(
        "B131289_All Wells -  Quantification Amplification Results_FAM.csv",
        "B131289_All Wells -  Quantification Amplification Results_HEX.csv",
    ),
    plate_map_type=PlateMapType.WELLLIT,
    plate_map_filename="20200411-171802_SP000151_tube_to_plate.csv",
    generated_output_filename="SP000151-B131289_cb_results.csv",
    reference_output_filename="SP000151-B131289_cb_results-for-comparison.csv",
    existence_output_filenames=("SP000151-B131289_final.pdf",),
)

# very bad plate
SP000147_B132297 = NormalRunSet(
    barcode="B132297",
    sop="SOP-V2",
    runinfo_filename="B132297_All Wells - Run Information.csv",
    quant_cq_filename="B132297_All Wells -  Quantification Cq Results.csv",
    amp_filenames=(
        "B132297_All Wells -  Quantification Amplification Results_FAM.csv",
        "B132297_All Wells -  Quantification Amplification Results_HEX.csv",
    ),
    plate_map_type=PlateMapType.WELLLIT,
    plate_map_filename="20200410-164913_SP000147_tube_to_plate.csv",
    generated_output_filename="SP000147-B132297_cb_results.csv",
    reference_output_filename="SP000147-B132297_cb_results-for-comparison.csv",
    existence_output_filenames=("SP000147-B132297_final.pdf",),
)


@pytest.mark.local_processing
@pytest.mark.parametrize(
    "runset",
    [
        SP000001_D041758,
        SP000002_D041761,
        SP000151_B131289,
        SP000147_B132297,
        SP000214_B131885,
        SP000114_B132312,
        pytest.param(SP000114_B132312_no_HEX, marks=pytest.mark.xfail),
        pytest.param(SP000114_B132312_bad_plate_map, marks=pytest.mark.xfail),
    ],
)
def test_local(tmp_path, runset):
    """
    Run a full test of local processing on a dataset. Checks for pdf creation
    and that the output csv matches our stored one.
    """
    runset.setup(EXAMPLE_FILE_DIR, tmp_path)
    if runset.plate_map_type == PlateMapType.LEGACY:
        plate_layout_arg = "--plate-layout"
    elif runset.plate_map_type == PlateMapType.WELLLIT:
        plate_layout_arg = "--well-lit"
    elif runset.plate_map_type == PlateMapType.HAMILTON:
        plate_layout_arg = "--hamilton"
    else:
        assert False, "Must specify a plate map"

    args = [
        "qpcr_processing",
        "--secret-id",
        "covid-19/google_test_creds",
        "local",
        "--protocol",
        runset.sop,
        "--qpcr-run-path",
        tmp_path,
        plate_layout_arg,
        tmp_path / runset.plate_map_dst_filename,
    ]

    subprocess.check_call(args)

    for existence_output_filename in runset.existence_output_filenames:
        assert (tmp_path / existence_output_filename).exists()

    with (tmp_path / runset.generated_output_filename).open("r") as t1, (
        EXAMPLE_FILE_DIR / runset.reference_output_filename
    ).open("r") as t2:
        rdr1 = csv.reader(t1)
        rdr2 = csv.reader(t2)
        for row1, row2, in zip(rdr1, rdr2):
            assert row1 == row2
