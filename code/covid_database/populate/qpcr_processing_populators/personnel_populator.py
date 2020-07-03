import logging
from abc import ABC
from typing import List

import pandas as pd

from covid_database.models.qpcr_processing import Institute, Researcher
from covid_database.populate.base import (
    BaseWorksheetPopulator,
    RemoteWorksheetPopulatorMixin,
)

log = logging.getLogger(__name__)


class PersonnelPopulator(BaseWorksheetPopulator, ABC):
    """Class that populates all data about personnel.
    """

    @property
    def models_to_populate(self) -> List[str]:
        """The models that the PersonnelPopulator will create and inset into the DB"""
        return [
            Institute.__name__,
            Researcher.__name__,
        ]

    def populate_models(self):
        """Create all models and insert into DB"""

        institutes = {inst.name: inst for inst in self.session.query(Institute).all()}
        researchers = []

        clia_certified = set(self.data["CLIA certified"].dropna())
        shift_supervisor = set(self.data["Shift supervisor"].dropna())

        for _, row in self.data.loc[:, ("Name", "Institution")].iterrows():
            if pd.isna(row).any():
                continue

            institute_name = row["Institution"]
            if institute_name not in institutes:
                log.debug(f"New institute {institute_name}")
                institutes[institute_name] = Institute(name=institute_name)

            researcher_name = row["Name"]
            researcher = (
                self.session.query(Researcher)
                .filter(Researcher.name == researcher_name)
                .one_or_none()
            )
            if researcher is None:
                log.debug(f"New researcher {researcher_name}")
                researchers.append(
                    Researcher(
                        name=researcher_name,
                        institute=institutes[institute_name],
                        clia_certified=row["Name"] in clia_certified,
                        supervisor=row["Name"] in shift_supervisor,
                    )
                )
            else:
                researcher.institute = institutes[institute_name]
                researcher.clia_certified = row["Name"] in clia_certified
                researcher.supervisor = row["Name"] in shift_supervisor

        log.info("populating institutes")
        self.session.add_all(institutes.values())
        self.session.flush()

        log.info("populating researchers")
        self.session.add_all(researchers)
        self.session.flush()


class RemotePersonnelPopulator(RemoteWorksheetPopulatorMixin, PersonnelPopulator):
    """Class that populates all relevant data from the Personnel worksheet of the
    FormChoices google sheet.
    """

    @property
    def spreadsheet_id_config_key(self) -> str:
        return "form_choice_spreadsheet_id"

    @property
    def sheet_name(self) -> str:
        return "Personnel"
