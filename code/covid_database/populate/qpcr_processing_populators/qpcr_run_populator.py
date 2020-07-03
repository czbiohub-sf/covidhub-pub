import logging
from abc import ABC
from typing import List

import pandas as pd

from covid_database.models.enums import Protocol
from covid_database.models.qpcr_processing import (
    QPCRPlate,
    QPCRRun,
    QPCRStation,
    Researcher,
)
from covid_database.populate.base import (
    BaseWorksheetPopulator,
    RemoteWorksheetPopulatorMixin,
)
from covidhub.constants.qpcr_forms import QPCRMetadata

log = logging.getLogger(__name__)


class QPCRRunPopulator(BaseWorksheetPopulator, ABC):
    """
    Class that populates all data about QPCR runs.
    """

    @property
    def models_to_populate(self) -> List[str]:
        return [QPCRRun.__name__]

    def populate_models(self):
        """
        Iterate through rows in the QPCR metadata form data and insert a QPCRRun entry
        for each row.
        """

        existing_barcodes = {
            qpcr_run.qpcr_plate.barcode for qpcr_run in self.session.query(QPCRRun)
        }

        log.info("populating qpcr_run models")
        for index, row in self.data.iterrows():
            if all(pd.isna(row)):
                continue

            barcode = row[QPCRMetadata.QPCR_PLATE_BARCODE]
            created_at = row[QPCRMetadata.TIMESTAMP]
            protocol = row[QPCRMetadata.PROTOCOL]

            if pd.isna(barcode):
                log.warning(
                    f"Row {index} in {QPCRMetadata.SHEET_NAME} is missing a "
                    "QPCR Plate Barcode, skipping this row"
                )
                continue
            elif barcode in existing_barcodes:
                continue

            researcher_name = row[QPCRMetadata.RESEARCHER_NAME]
            station_name = row[QPCRMetadata.QPCR_STATION]
            notes = row[QPCRMetadata.NOTES]

            if pd.isna(notes):
                # if notes are missing store null instead of 'NaN'
                notes = None

            station = (
                self.session.query(QPCRStation)
                .filter(QPCRStation.name == station_name)
                .one_or_none()
            )
            pcr_plate = (
                self.session.query(QPCRPlate)
                .filter(QPCRPlate.barcode == barcode)
                .one_or_none()
            )
            researcher = (
                self.session.query(Researcher)
                .filter(Researcher.name == researcher_name)
                .one_or_none()
            )

            if not pcr_plate or not researcher or not station or not protocol:
                log.critical(
                    f"Did not find models for run, skipping. Station: {station_name}, "
                    f"pcr_plate: {barcode}, researcher: {researcher_name}, "
                    f"protocol: {protocol}",
                    extra={"notify_slack": True},
                )
                continue
            qpcr_run = QPCRRun(
                qpcr=station,
                qpcr_plate=pcr_plate,
                researcher=researcher,
                notes=notes,
                created_at=created_at,
                protocol=Protocol(protocol.replace("SOP-V2-40", "SOP-V2")),
            )
            self.session.add(qpcr_run)


class RemoteQPCRRunPopulator(RemoteWorksheetPopulatorMixin, QPCRRunPopulator):
    """
    Class that populates all QPCRRun models from the google worksheet QPCR Metadata
    """

    @property
    def spreadsheet_id_config_key(self) -> str:
        return "collection_form_spreadsheet_id"

    @property
    def sheet_name(self) -> str:
        return QPCRMetadata.SHEET_NAME

    @property
    def skip_header(self) -> bool:
        return True
