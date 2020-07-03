import logging
from abc import ABC
from typing import List

import pandas as pd
from sqlalchemy.orm.exc import NoResultFound

import covidhub.constants.qpcr_forms as forms
from covid_database.models.enums import LabLocation, SamplePlateType
from covid_database.models.qpcr_processing import (
    Registration,
    Researcher,
    SamplePlate,
    SamplePlateMetadata,
)
from covid_database.populate.base import (
    BaseWorksheetPopulator,
    RemoteWorksheetPopulatorMixin,
)
from covidhub.constants import PlateMapType
from covidhub.constants.enums import ControlsMappingType

log = logging.getLogger(__name__)


class SampleRegistrationPopulator(BaseWorksheetPopulator, ABC):
    """
    Class that populates all sample registration data.
    """

    @property
    def models_to_populate(self) -> List[str]:
        return [SamplePlate.__name__]

    def populate_models(self):
        """
        Iterate through rows in Sample Registration form data and insert a SamplePlate entry
        for each registered plate
        """
        log.info(f"populating sample plates from {forms.SampleRegistration.SHEET_NAME}")

        existing_plates = {p.barcode for p in self.session.query(SamplePlate).all()}

        for index, row in self.data.iterrows():
            timestamp = row[forms.SampleRegistration.TIMESTAMP]
            researcher_name = row[forms.SampleRegistration.RESEARCHER_NAME]
            courier_name = row[forms.SampleRegistration.COURIER_NAME]
            notes = row[forms.SampleRegistration.NOTES]

            try:
                prepared_at = LabLocation(row[forms.SampleRegistration.PREPARED_AT])
            except ValueError:
                log.error(
                    f"Invalid {forms.SampleRegistration.PREPARED_AT} "
                    f"{row[forms.SampleRegistration.PREPARED_AT]} for sample plate row "
                    f"{index + 2}. Valid values are "
                    f"{list(e.value for e in LabLocation)}. Skipping this sample plate "
                    "registration."
                )
                continue

            try:
                researcher = (
                    self.session.query(Researcher)
                    .filter(Researcher.name == researcher_name)
                    .one()
                )
            except NoResultFound:
                log.exception(f"Unknown researcher {researcher_name}")
                raise

            sample_plates = []

            for columnname in forms.SampleRegistration.SAMPLE_PLATE_BARCODES:
                barcode = row[columnname]

                if pd.isnull(barcode):
                    continue
                elif barcode in existing_plates:
                    continue

                plate = self.look_for_barcode(barcode)
                if plate is None:
                    log.debug(f"Adding sample plate: {barcode}")
                    plate = SamplePlate(barcode=barcode, prepared_at=prepared_at)
                    self.session.add(plate)
                else:
                    log.debug(f"Updating sample plate: {barcode}")
                    plate.prepared_at = prepared_at

                sample_plates.append(plate)

            log.debug(
                f"Registering {len(sample_plates)} sample plates that arrived at "
                f"{timestamp} processed by {researcher_name}"
            )

            # don't register the sample if we've seen all the plates before
            if sample_plates:
                registration = Registration(
                    created_at=timestamp,
                    researcher=researcher,
                    notes=notes,
                    courier_name=courier_name,
                    sample_plates=sample_plates,
                )
                self.session.add(registration)

    def look_for_barcode(self, barcode):
        return (
            self.session.query(SamplePlate)
            .filter(SamplePlate.barcode == barcode)
            .one_or_none()
        )


class RemoteSampleRegistrationPopulator(
    RemoteWorksheetPopulatorMixin, SampleRegistrationPopulator
):
    """
    Class that populates all relevant data from the google worksheet Sample Registration
    """

    @property
    def spreadsheet_id_config_key(self) -> str:
        return "collection_form_spreadsheet_id"

    @property
    def sheet_name(self) -> str:
        return forms.SampleRegistration.SHEET_NAME

    @property
    def skip_header(self) -> bool:
        return True


class SamplePlateMetadataPopulator(BaseWorksheetPopulator):
    """
    Class that populates all sample metadata.
    """

    @property
    def models_to_populate(self) -> List[str]:
        return [SamplePlateMetadata.__name__, SamplePlate.__name__]

    def populate_models(self):
        """
        Iterate through rows in Sample Metadata form data and insert a SamplePlateMetadata entry
        for each sample plate metadata entry
        """
        log.info(f"populating sample plates from {forms.SampleMetadata.SHEET_NAME}")

        # set of plate ids which already have metadata added
        existing_metadata_barcodes = {
            md.sample_plate.barcode for md in self.session.query(SamplePlateMetadata)
        }

        new_barcodes = set()

        for index, row in self.data.iterrows():
            barcode = row[forms.SampleMetadata.SAMPLE_PLATE_BARCODE]
            if barcode in existing_metadata_barcodes:
                log.debug(f"Existing metadata found for {barcode}, skipping")
                continue
            elif barcode in new_barcodes:
                log.critical(
                    f"Duplicate barcode in {forms.SampleMetadata.SHEET_NAME}: "
                    f"{barcode}",
                    extra={"notify_slack": True},
                )
                continue

            new_barcodes.add(barcode)

            notes = row[forms.SampleMetadata.NOTES]
            researcher_name = row[forms.SampleMetadata.RESEARCHER_NAME]
            timestamp = row[forms.SampleMetadata.TIMESTAMP]

            try:
                sample_plate_type = SamplePlateType(
                    row[forms.SampleMetadata.SAMPLE_TYPE]
                )
            except ValueError:
                log.critical(
                    f"Invalid {forms.SampleMetadata.SAMPLE_TYPE} "
                    f"{row[forms.SampleMetadata.SAMPLE_TYPE]} for sample plate "
                    f"{barcode}. Valid values are "
                    f"{list(e.value for e in SamplePlateType)}. Skipping this metadata.",
                    extra={"notify_slack": True},
                )
                continue

            try:
                controls_type = ControlsMappingType(
                    row[forms.SampleMetadata.CONTROLS_TYPE]
                )
            except ValueError:
                log.critical(
                    f"Invalid {forms.SampleMetadata.CONTROLS_TYPE} "
                    f"{row[forms.SampleMetadata.CONTROLS_TYPE]} for sample plate"
                    f"{barcode}. Valid values are "
                    f"{list(e.value for e in ControlsMappingType)}. Skipping this "
                    f"metadata",
                    extra={"notify_slack": True},
                )
                continue

            try:
                plate_layout_format = PlateMapType(
                    row[forms.SampleMetadata.PLATE_LAYOUT_TYPE]
                )
            except ValueError:
                log.error(
                    f"Invalid {forms.SampleMetadata.PLATE_LAYOUT_TYPE} "
                    f"{row[forms.SampleMetadata.PLATE_LAYOUT_TYPE]} for sample plate "
                    f"{barcode}. Valid values are "
                    f"{list(e.value for e in PlateMapType)}. Skipping this metadata."
                )
                continue

            sample_source = row[forms.SampleMetadata.SAMPLE_SOURCE]

            try:
                researcher = (
                    self.session.query(Researcher)
                    .filter(Researcher.name == researcher_name)
                    .one()
                )
            except NoResultFound:
                log.exception(f"Unknown researcher {researcher_name}")
                raise

            if pd.isnull(barcode):
                log.error(
                    f"Row {index} in sheet {forms.SampleMetadata.SHEET_NAME} contains "
                    "blank sample plate barcode, skipping this metadata."
                )
                continue

            plate = self.look_for_barcode(barcode)
            if plate is None:
                if sample_plate_type != SamplePlateType.ORIGINAL:
                    # Per Emily, we allow submission of sample plate
                    # metadata for all but original plates that haven't been
                    # previously registered. In this situation, we
                    # create the SamplePlate object.
                    plate = SamplePlate(barcode=barcode, prepared_at=LabLocation.BIOHUB)
                    self.session.add(plate)
                else:
                    # All other plate types must have been registered first
                    log.error(
                        f"Encountered Sample Plate Metadata for Sample Plate {barcode} "
                        "that wasn't previously registered, skipping this metadata."
                    )
                    continue

            metadata = SamplePlateMetadata(
                created_at=timestamp,
                researcher=researcher,
                notes=notes,
                sample_plate=plate,
                controls_type=controls_type,
                sample_source=sample_source,
                plate_layout_format=plate_layout_format,
                sample_plate_type=sample_plate_type,
            )

            self.session.add(metadata)

    def look_for_barcode(self, barcode):
        return (
            self.session.query(SamplePlate)
            .filter(SamplePlate.barcode == barcode)
            .one_or_none()
        )


class RemoteSamplePlateMetadataPopulator(
    RemoteWorksheetPopulatorMixin, SamplePlateMetadataPopulator
):
    """
    Class that populates all relevant data from the google worksheet Sample Metadata
    """

    @property
    def spreadsheet_id_config_key(self) -> str:
        return "collection_form_spreadsheet_id"

    @property
    def sheet_name(self) -> str:
        return forms.SampleMetadata.SHEET_NAME

    @property
    def skip_header(self) -> bool:
        return True
