import logging
from abc import ABC
from typing import List

import pandas as pd
from sqlalchemy.orm.exc import NoResultFound

import covidhub.constants.qpcr_forms as forms
from covid_database.models.qpcr_processing import (
    Freezer,
    FreezerCheckout,
    Plate,
    Researcher,
)
from covid_database.populate.base import (
    BaseWorksheetPopulator,
    RemoteWorksheetPopulatorMixin,
)

log = logging.getLogger(__name__)


class FreezerCheckoutPopulator(BaseWorksheetPopulator, ABC):
    """
    Class that populates all data about freezer checkouts.
    """

    @property
    def models_to_populate(self) -> List[str]:
        return [
            FreezerCheckout.__name__,
        ]

    def populate_models(self):
        """
        Iterate through rows in minus80 Checkout form
        """
        log.info("populating freezer check-outs...")

        existing_plates_times = {
            (m.plate, m.created_at) for m in self.session.query(FreezerCheckout).all()
        }

        for index, row in self.data.iterrows():
            # for empty rows
            if all(pd.isna(row)):
                continue

            timestamp = row[forms.FreezerCheckout.TIMESTAMP]
            researcher_name = row[forms.FreezerCheckout.RESEARCHER_NAME]
            sample_barcode = row[forms.FreezerCheckout.SAMPLE_PLATE_BARCODE]
            freezer_name = row[forms.FreezerCheckout.FREEZER]
            rna_barcode = row[forms.FreezerCheckout.RNA_PLATE_BARCODE]
            notes = row[forms.FreezerCheckout.NOTES]

            # make sure that the sample barcode or rna barcode is valid
            if not pd.isna(sample_barcode) and pd.isna(rna_barcode):
                barcode = sample_barcode
            elif not pd.isna(rna_barcode) and pd.isna(sample_barcode):
                barcode = rna_barcode
            elif not pd.isna(sample_barcode) and not pd.isna(rna_barcode):
                log.critical(
                    f"WARNING: this freezer checkout entry has multiple barcodes -- :\n rna barcode: {rna_barcode} \n sample plate barcode: {sample_barcode}, skipping",
                    extra={"notify_slack": True},
                )
                continue
            else:
                log.critical(
                    f"Can't find a barcode for freezer checkout: {timestamp} {researcher_name}",
                    extra={"notify_slack": True},
                )
                continue

            try:
                plate = self.session.query(Plate).filter(Plate.barcode == barcode).one()
            except NoResultFound:
                log.debug(f"Can't find plate {barcode}, skipping")
                continue

            if (plate, timestamp) in existing_plates_times:
                continue

            if not pd.isna(freezer_name):
                try:
                    freezer = (
                        self.session.query(Freezer)
                        .filter(Freezer.name == freezer_name)
                        .one()
                    )
                except NoResultFound:
                    log.critical(
                        f"Error finding freezer {freezer_name}",
                        extra={"notify_slack": True},
                    )
                    return
            else:
                log.critical(
                    f"missing freezer name for plate {barcode}",
                    extra={"notify_slack": True},
                )
                continue

            try:
                researcher = (
                    self.session.query(Researcher)
                    .filter(Researcher.name == researcher_name)
                    .one()
                )
            except NoResultFound:
                log.critical(
                    f"Error finding researcher {researcher_name}",
                    extra={"notify_slack": True},
                )
                return

            log.debug(
                f"{sample_barcode, rna_barcode} checked out of {freezer_name} at {timestamp}"
            )
            freezer_checkout = FreezerCheckout(
                created_at=timestamp,
                researcher=researcher,
                plate=plate,
                freezer=freezer,
                notes=notes,
            )
            self.session.add(freezer_checkout)


class RemoteFreezerCheckoutPopulator(
    RemoteWorksheetPopulatorMixin, FreezerCheckoutPopulator
):
    """
    Class that populates all relevant data from the google worksheet 'minus 80 Checkout'
    """

    @property
    def spreadsheet_id_config_key(self) -> str:
        return "collection_form_spreadsheet_id"

    @property
    def sheet_name(self) -> str:
        return forms.FreezerCheckout.SHEET_NAME

    @property
    def skip_header(self) -> bool:
        return True
