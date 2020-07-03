import logging
from abc import ABC
from typing import List

from sqlalchemy.orm.exc import NoResultFound

import covidhub.constants.qpcr_forms as forms
from covid_database.models.qpcr_processing import (
    Aliquoting,
    BravoStation,
    QPCRPlate,
    Researcher,
    RNAPlate,
)
from covid_database.populate.base import (
    BaseWorksheetPopulator,
    RemoteWorksheetPopulatorMixin,
)

log = logging.getLogger(__name__)


class RNARerunPopulator(BaseWorksheetPopulator, ABC):
    """
    Class that populates all RNA plate reruns.
    """

    @property
    def models_to_populate(self) -> List[str]:
        return [Aliquoting.__name__]

    def populate_models(self):
        """
        Iterate through rows in ReRun RNA Plate form data and insert Aliquoting entries for each registered plate
        """
        log.info("populating Aliquoting (reruns)")

        existing_aliquoting = {
            m.qpcr_plate.barcode for m in self.session.query(Aliquoting).all()
        }

        for index, row in self.data.iterrows():
            timestamp = row[forms.RNARerun.TIMESTAMP]
            researcher_name = row[forms.RNARerun.RESEARCHER_NAME]
            notes = row[forms.RNARerun.NOTES]
            try:
                researcher = (
                    self.session.query(Researcher)
                    .filter(Researcher.name == researcher_name)
                    .one()
                )
            except NoResultFound:
                log.exception(f"Unknown researcher {researcher_name}")
                raise

            rna_barcode = row[forms.RNARerun.RNA_PLATE_BARCODE]
            rna_plate = self.get_rna_plate(rna_barcode)
            if rna_plate is None:
                logging.debug(f"No RNA plate found for {rna_barcode}, skipping")
                continue

            qpcr_barcode = row[forms.RNARerun.QPCR_PLATE_BARCODE]
            if qpcr_barcode in existing_aliquoting:
                continue

            qpcr_plate = self.get_qpcr_plate(qpcr_barcode)
            bravo_station = self.get_bravo(row[forms.RNARerun.BRAVO_STATION])

            aliquoting = Aliquoting(
                created_at=timestamp,
                bravo=bravo_station,
                researcher=researcher,
                rna_plate=rna_plate,
                qpcr_plate=qpcr_plate,
                notes=notes,
            )

            log.debug(f"Adding Aliquoting {aliquoting}")
            self.session.add(aliquoting)

        self.session.flush()

    def get_bravo(self, bravo_station_name: str) -> BravoStation:
        """Get a BravoStation. These should always exist"""

        try:
            bravo_station = (
                self.session.query(BravoStation)
                .filter(BravoStation.name == bravo_station_name)
                .one()
            )
        except NoResultFound:
            logging.exception(f"No Bravo found for {bravo_station_name}")
            raise

        return bravo_station

    def get_rna_plate(self, rna_barcode: str) -> RNAPlate:
        """Return an RNAPlate instance, error none found."""

        # TODO: raise exception once the data is clean
        rna_plate = (
            self.session.query(RNAPlate)
            .filter(RNAPlate.barcode == rna_barcode)
            .one_or_none()
        )

        return rna_plate

    def get_qpcr_plate(self, qpcr_barcode: str) -> QPCRPlate:
        """Find the qPCR plate that was aliquoted into. This should always exist because
        it was prepped by the reagent team.
        """

        try:
            qpcr_plate = (
                self.session.query(QPCRPlate)
                .filter(QPCRPlate.barcode == qpcr_barcode)
                .one()
            )
        except NoResultFound:
            log.exception(f"No qpcr plate found with barcode {qpcr_barcode}")
            raise

        return qpcr_plate


class RemoteRNARerunPopulator(RemoteWorksheetPopulatorMixin, RNARerunPopulator):
    """
    Class that populates all relevant data from the google worksheet ReRun RNA Plate
    """

    @property
    def spreadsheet_id_config_key(self) -> str:
        return "collection_form_spreadsheet_id"

    @property
    def sheet_name(self) -> str:
        return forms.RNARerun.SHEET_NAME

    @property
    def skip_header(self) -> bool:
        return True
