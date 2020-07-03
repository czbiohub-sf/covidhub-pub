import logging
from abc import ABC
from typing import List

from covid_database.models.qpcr_processing import (
    BravoStation,
    Freezer,
    Fridge,
    QPCRStation,
)
from covid_database.populate.base import (
    BaseWorksheetPopulator,
    RemoteWorksheetPopulatorMixin,
)

log = logging.getLogger(__name__)


class FormChoicesPopulator(BaseWorksheetPopulator, ABC):
    """
    Class that populates all data about QPCRStation, BravoStation, Fridges, and
    Freezers.
    """

    @property
    def models_to_populate(self) -> List[str]:
        """The models that the FormChoicesPopulator will create and inset into the DB"""
        return [
            QPCRStation.__name__,
            BravoStation.__name__,
            Fridge.__name__,
            Freezer.__name__,
        ]

    def add_new(self, model, form_data):
        existing_names = {m.name for m in self.session.query(model).all()}
        self.session.add_all(
            model(name=name) for name in form_data if name not in existing_names
        )

    def populate_models(self):
        """Create all models and insert into DB"""
        log.info("populating PCR machines")
        self.add_new(QPCRStation, self.data["PCR machine"].dropna())

        log.info("populating Bravo machines")
        self.add_new(BravoStation, self.data["Bravo Machine"].dropna())

        log.info("populating Fridges")
        self.add_new(Fridge, self.data["Fridge"].dropna())

        log.info("populating Freezers")
        self.add_new(Freezer, self.data["Freezer"].dropna())


class RemoteFormChoicesPopulator(RemoteWorksheetPopulatorMixin, FormChoicesPopulator):
    """
    Class that populates all relevant data from the google worksheet FormChoices
    """

    @property
    def spreadsheet_id_config_key(self) -> str:
        return "form_choice_spreadsheet_id"

    @property
    def sheet_name(self) -> str:
        return "FormChoices"
