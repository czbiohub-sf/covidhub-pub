import pytest

from comet.lib.external_sample_shipment import (
    verify_collaborator_sample_data,
    verify_dph_sample_data,
)
from covidhub.constants.comet_forms import CollaboratorSampleMetadata, DPHSampleMetadata


def test_verify_dph_sample_data(fake_dph_metadata_shipment, time_now):
    """Test properly formatted dph data"""
    sample_data = verify_dph_sample_data(fake_dph_metadata_shipment, time_now)
    # verify new columns were added
    assert DPHSampleMetadata.EXTRACTION_METHOD in sample_data.columns
    assert DPHSampleMetadata.DATE_RECEIVED in sample_data.columns


def test_error_on_missing_data(fake_dph_metadata_shipment_missing_data, time_now):
    """Test we provide helpful error message if required value missing"""
    with pytest.raises(ValueError) as error:
        verify_dph_sample_data(fake_dph_metadata_shipment_missing_data, time_now)
    assert "MISSING DATA: Collection Date, for accession 17" in str(error.value)


def test_veriify_collaborator_sample_data(
    fake_collaborator_metadata_shipment, time_now
):
    """Test properly formatted collaborator data"""
    sample_data = verify_collaborator_sample_data(
        fake_collaborator_metadata_shipment, time_now
    )
    assert CollaboratorSampleMetadata.DATE_RECEIVED in sample_data.columns


def test_error_on_missing_column(
    fake_collaborator_metadata_shipment_bad_column, time_now
):
    """Test we provide helpful error message if column missing"""
    with pytest.raises(ValueError) as error:
        verify_collaborator_sample_data(
            fake_collaborator_metadata_shipment_bad_column, time_now
        )
    assert "Sample data missing mandatory column : Unique Identifier" in str(
        error.value
    )


def test_add_optional_collaborator_sample_column(
    fake_collaborator_metadata_shipment_missing_optional_column, time_now
):
    """Test that we add in optional columns if they're missing"""
    sample_data = verify_collaborator_sample_data(
        fake_collaborator_metadata_shipment_missing_optional_column, time_now
    )
    assert CollaboratorSampleMetadata.COLLECTION_DATE in sample_data.columns
    assert CollaboratorSampleMetadata.ZIP_PREFIX in sample_data.columns
