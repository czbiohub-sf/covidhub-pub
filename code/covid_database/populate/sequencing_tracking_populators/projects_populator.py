import logging
from abc import ABC
from typing import List

from covid_database.models.enums import ContractStatus, NGSProjectType
from covid_database.models.ngs_sample_tracking import Project
from covid_database.populate.base import (
    BaseWorksheetPopulator,
    RemoteWorksheetPopulatorMixin,
)

log = logging.getLogger(__name__)


class ProjectsPopulator(BaseWorksheetPopulator, ABC):
    """
    Class that populates all COMET projects.
    """

    @property
    def models_to_populate(self) -> List[str]:
        """The models that the SubmittersPopulator will create and inset into the DB"""
        return [Project.__name__]

    def populate_models(self):
        """Create all models and insert into DB"""
        existing_project_models = self.session.query(Project).all()
        existing_project_rr_ids = {
            result.rr_project_id for result in existing_project_models
        }

        for index, row in self.data.iterrows():
            rr_project_id = row["RR_project_ID"]
            if rr_project_id in existing_project_rr_ids:
                continue
            cliahub_site_id = row["site_id"]
            contact_name = row["collaborater_name"]
            collaborating_institution = row["collaborating _institution"]
            objectives = row["objectives"]
            contract_status = ContractStatus(row["contract_status"])
            public = bool(row["public"])
            project_type = NGSProjectType(row["type"])
            microbial_allowed = bool(row["microbial_allowed"])
            sars_cov2_allowed = bool(row["sars-cov2 allowed"])
            transcriptome_allowed = bool(row["transcriptome_allowed"])

            self.session.add(
                Project(
                    rr_project_id=rr_project_id,
                    cliahub_site_id=cliahub_site_id,
                    collaborating_institution=collaborating_institution,
                    objective=objectives,
                    contact_name=contact_name,
                    public=public,
                    contract_status=contract_status,
                    type=project_type,
                    microbial_allowed=microbial_allowed,
                    sars_cov2_allowed=sars_cov2_allowed,
                    transcriptome_allowed=transcriptome_allowed,
                )
            )


class RemoteProjectsPopulator(RemoteWorksheetPopulatorMixin, ProjectsPopulator):
    """
    Class that populates all relevant data from the google worksheet COMET Input Plate
    """

    @property
    def spreadsheet_id_config_key(self) -> str:
        return "project_sheet_id"

    @property
    def sheet_name(self) -> str:
        return "Sheet1"
