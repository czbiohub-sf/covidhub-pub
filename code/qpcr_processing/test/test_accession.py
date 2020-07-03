import pytest

from covidhub.constants import ControlType, PlateMapType
from covidhub.error import InvalidWellID
from qpcr_processing import accession
from qpcr_processing.well_results import WellResults


def test_well_mapping_for_hamilton(
    hamilton_plate_layout, expected_hamilton_accession_data, standard_control_wells
):
    accession_data = accession.process_hamilton(hamilton_plate_layout)
    accession_data.update(standard_control_wells)
    assert accession_data == expected_hamilton_accession_data


def test_well_mapping_for_welllit(
    welllit_plate_layout, expected_welllit_accession_data, standard_control_wells
):
    accession_data = accession.process_welllit(welllit_plate_layout)
    accession_data.update(standard_control_wells)
    assert accession_data == expected_welllit_accession_data


def test_well_mapping_legacy_plate_layout(
    legacy_plate_layout, expected_legacy_accession_data
):
    accession_data = accession.parse_legacy_accession_data(legacy_plate_layout)
    assert accession_data == expected_legacy_accession_data


def test_results_get_well_lit_accession_data(expected_welllit_accession_data):
    expected_results = {
        "B1": WellResults(accession="ACCTEST1"),
        "C1": WellResults(accession="ACCTEST2"),
    }
    results = {
        "B1": WellResults(),
        "C1": WellResults(),
    }

    results = accession.add_accession_barcodes_to_results(
        results, expected_welllit_accession_data
    )

    assert results == expected_results


def test_results_get_legacy_accession_data(expected_legacy_accession_data):
    expected_results = {
        "B1": WellResults(accession="LEGTEST1"),
        "A7": WellResults(accession="LEGTEST4"),
    }
    results = {
        "B1": WellResults(),
        "A7": WellResults(),
    }

    results = accession.add_accession_barcodes_to_results(
        results, expected_legacy_accession_data
    )

    assert results == expected_results


def test_bad_hamilton_data(bad_hamilton_layout):
    with pytest.raises(InvalidWellID):
        accession.read_accession_data(PlateMapType.HAMILTON, bad_hamilton_layout)


def test_bad_welllit_data(bad_welllit_layout):
    with pytest.raises(InvalidWellID):
        accession.read_accession_data(PlateMapType.WELLLIT, bad_welllit_layout)


@pytest.mark.integtest
def test_hamilton_accession_with_drive(
    gdrive_service,
    gdrive_hamilton_folder,
    sample_metadata_sheet,
    sample_plate_barcode,
    standard_control_wells,
):
    expected_results = {
        "A1": WellResults(accession=ControlType.NTC, control_type=ControlType.NTC),
        "B1": WellResults(accession="S47399"),
    }
    results = {"A1": WellResults(control_type=ControlType.NTC), "B1": WellResults()}

    accession_data = accession.get_accession_data(
        gdrive_service,
        gdrive_hamilton_folder,
        sample_metadata_sheet,
        sample_plate_barcode,
    )
    accession_data.update(standard_control_wells)
    results = accession.add_accession_barcodes_to_results(results, accession_data)

    assert results == expected_results


@pytest.mark.integtest
def test_welllit_accession_with_drive(
    gdrive_service,
    gdrive_welllit_folder,
    sample_metadata_sheet,
    sample_plate_barcode,
    standard_control_wells,
):
    expected_results = {
        "A1": WellResults(accession=ControlType.NTC, control_type=ControlType.NTC),
        "B1": WellResults(accession="ACCTEST1"),
    }
    results = {"A1": WellResults(control_type=ControlType.NTC), "B1": WellResults()}

    accession_data = accession.get_accession_data(
        gdrive_service,
        gdrive_welllit_folder,
        sample_metadata_sheet,
        sample_plate_barcode,
    )
    accession_data.update(standard_control_wells)
    results = accession.add_accession_barcodes_to_results(results, accession_data)

    assert results == expected_results


@pytest.mark.integtest
def test_legacy_accession_with_drive(
    gdrive_service,
    gdrive_legacy_folder,
    sample_metadata_sheet,
    sample_plate_barcode,
    standard_control_wells,
):
    expected_results = {
        "A1": WellResults(accession=ControlType.NTC, control_type=ControlType.NTC),
        "B1": WellResults(accession="LEGTEST1"),
    }
    results = {"A1": WellResults(control_type=ControlType.NTC), "B1": WellResults()}

    accession_data = accession.get_accession_data(
        gdrive_service,
        gdrive_legacy_folder,
        sample_metadata_sheet,
        sample_plate_barcode,
    )
    accession_data.update(standard_control_wells)
    results = accession.add_accession_barcodes_to_results(results, accession_data)

    assert results == expected_results
