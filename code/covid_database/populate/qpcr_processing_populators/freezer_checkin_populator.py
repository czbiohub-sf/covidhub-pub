import logging
from abc import ABC
from typing import List

import pandas as pd
from sqlalchemy.orm.exc import NoResultFound

import covidhub.constants.qpcr_forms as forms
from covid_database.models.enums import FreezerBlock
from covid_database.models.qpcr_processing import (
    Freezer,
    FreezerCheckin,
    Plate,
    Researcher,
)
from covid_database.populate.base import (
    BaseWorksheetPopulator,
    RemoteWorksheetPopulatorMixin,
)

log = logging.getLogger(__name__)


def sanitize_block(block):
    return (
        str(block)
        .replace("Block ", "")
        .replace("[front]", "")
        .replace("[back]", "")
        .strip()
    )


class FreezerCheckinPopulator(BaseWorksheetPopulator, ABC):
    """
    Class that populates all data about freezer checkins.
    """

    @property
    def models_to_populate(self) -> List[str]:
        return [
            FreezerCheckin.__name__,
        ]

    def get_block(self, block_a, block_b):
        block = block_a
        if not pd.isna(block_a):
            block = "A" + sanitize_block(block_a)
        elif not pd.isna(block_b):
            block = "B" + sanitize_block(block_b)
        else:
            log.debug(f"Invalid blocks {block_a}, {block_b}, skipping")
        return block

    def add_freezer_checkin(
        self,
        barcode,
        timestamp,
        existing_plates_times,
        freezer_name,
        block,
        shelf,
        rack,
        notes,
        researcher_name,
        ix,
    ):
        try:
            plate = self.session.query(Plate).filter(Plate.barcode == barcode).one()
        except NoResultFound:
            log.debug(f"Can't find plate {barcode}, skipping")
            return

        if (plate, timestamp) in existing_plates_times:
            return

        try:
            shelf = int(shelf)
            rack = int(rack)
        except ValueError:
            log.critical(
                f"Invalid shelf {shelf} or rack {rack} in row {ix}, skipping",
                extra={"notify_slack": True},
            )
            return

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
            return

        try:
            block = FreezerBlock[block]
        except KeyError:
            log.critical(
                f"Invalid block {block} for plate {barcode} on row {ix}, skipping",
                extra={"notify_slack": True},
            )
            return

        try:
            researcher = (
                self.session.query(Researcher)
                .filter(Researcher.name == researcher_name)
                .one()
            )
        except NoResultFound:
            log.critical(
                f"Error finding researcher {researcher_name} on row {ix}",
                extra={"notify_slack": True},
            )
            return

        log.debug(f"{plate} checked in to {freezer_name} at {timestamp}")

        freezer_checkin = FreezerCheckin(
            created_at=timestamp,
            researcher=researcher,
            freezer=freezer,
            shelf=shelf,
            rack=rack,
            block=block,
            notes=notes,
            plate=plate,
        )
        self.session.add(freezer_checkin)

    def populate_models(self):
        """
        Iterate through rows in minus80 Checkin form
        """
        log.info("populating freezer check-ins...")

        existing_plates_times = {
            (m.plate, m.created_at) for m in self.session.query(FreezerCheckin).all()
        }

        for index, row in self.data.iterrows():
            # for empty rows
            if all(pd.isna(row)):
                continue

            ix = index + 3  # because google sheet has two header rows and is 1-indexed
            timestamp = row[forms.FreezerCheckin.TIMESTAMP]
            researcher_name = str(row[forms.FreezerCheckin.RESEARCHER_NAME])
            sample_barcode = row[forms.FreezerCheckin.SAMPLE_PLATE_BARCODE]
            rna_barcode = row[forms.FreezerCheckin.RNA_PLATE_BARCODE]
            notes = row[forms.FreezerCheckin.NOTES]
            sample_type = row[forms.FreezerCheckin.SAMPLE_TYPE]

            if pd.isna(notes):
                # Store null instead of NaN in the database
                notes = None

            # make sure that the sample barcode or rna barcode is valid
            if not pd.isna(sample_barcode) and pd.isna(rna_barcode):
                barcode = sample_barcode
                freezer_name = row[forms.FreezerCheckin.FREEZER]
                shelf = row[forms.FreezerCheckin.SHELF]
                rack = row[forms.FreezerCheckin.RACK]
                block = self.get_block(
                    row[forms.FreezerCheckin.BLOCK_A], row[forms.FreezerCheckin.BLOCK_B]
                )
                self.add_freezer_checkin(
                    barcode,
                    timestamp,
                    existing_plates_times,
                    freezer_name,
                    block,
                    shelf,
                    rack,
                    notes,
                    researcher_name,
                    ix,
                )
            elif not pd.isna(rna_barcode) and pd.isna(sample_barcode):
                barcode = rna_barcode
                freezer_name = row[forms.FreezerCheckin.RNA_FREEZER]
                shelf = row[forms.FreezerCheckin.RNA_SHELF]
                rack = row[forms.FreezerCheckin.RNA_RACK]
                block = self.get_block(
                    row[forms.FreezerCheckin.RNA_BLOCK_A],
                    row[forms.FreezerCheckin.RNA_BLOCK_B],
                )
                self.add_freezer_checkin(
                    barcode,
                    timestamp,
                    existing_plates_times,
                    freezer_name,
                    block,
                    shelf,
                    rack,
                    notes,
                    researcher_name,
                    ix,
                )
            elif sample_type == '"re-check-in"':
                for columnname in forms.FreezerCheckin.RNA_RECHECKIN_BARCODES:
                    barcode = row[columnname]
                    if pd.isnull(barcode):
                        continue
                    try:
                        plate = (
                            self.session.query(Plate)
                            .filter(Plate.barcode == barcode)
                            .one()
                        )
                    except NoResultFound:
                        log.debug(f"Can't find plate {barcode}, skipping")
                        continue

                    if (plate, timestamp) in existing_plates_times:
                        continue

                    try:
                        freezer_checkin = (
                            self.session.query(FreezerCheckin)
                            .filter(FreezerCheckin.plate == plate)
                            .one()
                        )
                    except NoResultFound:
                        log.error(
                            f"Can't find existing checkin for recheckin {barcode}, skipping"
                        )
                        continue
                    freezer_name = freezer_checkin.freezer.name
                    shelf = freezer_checkin.shelf
                    rack = freezer_checkin.rack
                    block = freezer_checkin.block.name
                    self.add_freezer_checkin(
                        barcode,
                        timestamp,
                        existing_plates_times,
                        freezer_name,
                        block,
                        shelf,
                        rack,
                        notes,
                        researcher_name,
                        ix,
                    )
            elif not pd.isna(sample_barcode) and not pd.isna(rna_barcode):
                log.critical(
                    f"freezer checkin on line {ix} specifies both a sample "
                    "plate barcode and an RNA plate barcode -- :\nrna barcode: "
                    f"{rna_barcode}\nsample plate barcode: {sample_barcode}, skipping",
                    extra={"notify_slack": True},
                )
                continue
            else:
                log.critical(
                    f"Can't find a barcode for freezer checkin on row {ix}: {timestamp}"
                    f" {researcher_name}, skipping",
                    extra={"notify_slack": True},
                )
                continue


class RemoteFreezerCheckinPopulator(
    RemoteWorksheetPopulatorMixin, FreezerCheckinPopulator
):
    """
    Class that populates all relevant data from the google worksheet 'minus 80 Checkin'
    """

    @property
    def spreadsheet_id_config_key(self) -> str:
        return "collection_form_spreadsheet_id"

    @property
    def sheet_name(self) -> str:
        return forms.FreezerCheckin.SHEET_NAME

    @property
    def skip_header(self) -> bool:
        return True
