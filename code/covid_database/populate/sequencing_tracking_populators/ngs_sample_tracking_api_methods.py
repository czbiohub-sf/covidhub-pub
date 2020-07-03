from typing import List, Set

import pandas as pd
from sqlalchemy.orm import Session

from covid_database.models.enums import NGSProjectType
from covid_database.models.ngs_sample_tracking import (
    CollaboratorCZBID,
    CZBID,
    DphCZBID,
    Project,
)
from covidhub.constants.comet_forms import CollaboratorSampleMetadata, DPHSampleMetadata

CZB_ID_LENGTH = 5


def get_project_model(rr_project_code: str, session: Session):
    """
    Query for an existing project model by rr_project_code
    :param rr_project_code:
    :param session:
    :return:
    """
    return (
        session.query(Project)
        .filter(Project.rr_project_id == rr_project_code)
        .one_or_none()
    )


def _get_next_available_czb_ids_for_project(
    project: Project, session: Session, number_needed: int
) -> List[str]:
    """
    Lookup the latest czb_id value assigned to the given project and generate the number of new czb_ids
    requested.

    Parameters
    ----------

    project :
        The project we want to add czb_ids to
    session :
        An open DB session object
    number_needed :
        The number of czb_ids to generate

    Returns
    --------
    a list of newly generated czb_ids
    """
    czb_id_models = session.query(CZBID).filter(CZBID.project_id == project.id).all()
    if len(czb_id_models) == 0:
        # no existing czb_ids, start from 1
        next_val = 1
    else:
        id_values = [int(czb_model.czb_id.split("_")[1]) for czb_model in czb_id_models]
        next_val = max(id_values) + 1
    new_czb_ids = []
    for val in range(next_val, next_val + number_needed):
        new_czb_ids.append(f"{project.rr_project_id}_{str(val).zfill(CZB_ID_LENGTH)}")
    return new_czb_ids


def get_all_external_accessions_for_project(project: Project, session: Session) -> Set:
    """Return all external accessions from a specific project as a a set"""
    return {
        result.external_accession
        for result in session.query(DphCZBID).filter(DphCZBID.project_id == project.id)
    }


def populate_new_czb_ids_from_metadata(
    project: Project, sample_metadata: pd.DataFrame, session: Session
) -> pd.DataFrame:
    """Generate CZBID's for a new batch of sample metadata and insert into DB

    Parameters
    -----------

    project :
        The project associated with the new samples
    sample_metadata :
        The metadata associated with the new samples
    """
    # generate new czb_ids and assign
    new_czb_ids = _get_next_available_czb_ids_for_project(
        project, session, len(sample_metadata)
    )
    sample_metadata[DPHSampleMetadata.CZB_ID] = new_czb_ids
    for idx, row in sample_metadata.iterrows():
        if project.type == NGSProjectType.DPH:
            session.add(
                DphCZBID(
                    project_id=project.id,
                    czb_id=row[DPHSampleMetadata.CZB_ID],
                    initial_volume=row[DPHSampleMetadata.INITIAL_VOLUME],
                    external_accession=row[DPHSampleMetadata.EXTERNAL_ACCESSION],
                    collection_date=row[DPHSampleMetadata.COLLECTION_DATE],
                    zip_prefix=row[DPHSampleMetadata.ZIP_PREFIX],
                    container_name=row[DPHSampleMetadata.CONTAINER_NAME],
                    extraction_method=row[DPHSampleMetadata.EXTRACTION_METHOD],
                    specimen_source=row[DPHSampleMetadata.SPECIMEN_TYPE],
                    date_received=row[DPHSampleMetadata.DATE_RECEIVED],
                )
            )
        if project.type == NGSProjectType.OTHER:
            session.add(
                CollaboratorCZBID(
                    project_id=project.id,
                    czb_id=row[CollaboratorSampleMetadata.CZB_ID],
                    initial_volume=row[CollaboratorSampleMetadata.INITIAL_VOLUME],
                    external_accession=row[
                        CollaboratorSampleMetadata.EXTERNAL_ACCESSION
                    ],
                    collection_date=row[CollaboratorSampleMetadata.COLLECTION_DATE],
                    specimen_source=row[CollaboratorSampleMetadata.SPECIMEN_TYPE],
                    zip_prefix=row[CollaboratorSampleMetadata.ZIP_PREFIX],
                    notes=row[CollaboratorSampleMetadata.NOTES],
                )
            )
    return sample_metadata
