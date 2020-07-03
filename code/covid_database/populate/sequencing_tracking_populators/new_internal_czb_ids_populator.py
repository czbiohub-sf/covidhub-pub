import logging
from abc import ABC
from typing import List

from covid_database.models.enums import NGSProjectType
from covid_database.models.ngs_sample_tracking import (
    CZBID,
    CZBIDRnaPlate,
    InternalCZBID,
)
from covid_database.models.qpcr_processing import RNAPlate
from covid_database.populate.base import (
    BaseWorksheetPopulator,
    RemoteWorksheetPopulatorMixin,
)
from covid_database.populate.sequencing_tracking_populators.utils import ProjectHandler

log = logging.getLogger(__name__)


class NewInternalCZBIDPopulator(BaseWorksheetPopulator, ABC):
    """
    This class populates any missing czb_ids.
    """

    @property
    def models_to_populate(self) -> List[str]:
        """The models that the SequencingPlatesPopulator will create and inset into the DB"""
        return [InternalCZBID.__name__, CZBIDRnaPlate.__name__]

    def populate_models(self):
        """Create all models and insert into DB"""
        log.info("Populating missing czb_ids from og_plates megasheet")

        # get all existing czb_ids
        existing_czb_id_models = self.session.query(CZBID).all()
        existing_czb_ids = {result.czb_id for result in existing_czb_id_models}

        # get czb_ids from mega sheet
        og_plates_czb_ids = set(self.data["CZB_ID"].values)
        missing_czb_ids = og_plates_czb_ids - existing_czb_ids

        projects_handler = ProjectHandler(session=self.session)

        for czb_id in missing_czb_ids:
            czb_id_info = self.data[self.data["CZB_ID"] == czb_id]
            # check for 96 plate barcode
            rna_plate = list(czb_id_info["96 RNA Plate Barcode"].dropna().values)
            if len(rna_plate) == 0:
                continue
            rna_plate_barcode = rna_plate[0]
            well_info = list(czb_id_info["96 RNA Plate Well"].dropna().values)
            if len(well_info) == 0:
                log.error(f"internal czb_id: {czb_id} missing source well info")
                continue
            well_id = well_info[0]

            # create czb_id model
            project = projects_handler.get_project_from_czb_id(czb_id=czb_id)
            if not project:
                log.critical(f"No project found for : {czb_id}")
                continue
            if project.type != NGSProjectType.INTERNAL:
                log.error(f"czb_id {czb_id} is not an internal id")
                continue
            czb_id_model = InternalCZBID(czb_id=czb_id, project_id=project.id)
            self.session.add(czb_id_model)
            self.session.flush()
            # get rna_plate entry
            rna_plate_model = (
                self.session.query(RNAPlate)
                .filter(RNAPlate.barcode == rna_plate_barcode)
                .one_or_none()
            )
            if not rna_plate_model:
                log.error(f"No rna plate found for rna barcde {rna_plate_barcode}")
                continue
            self.session.add(
                CZBIDRnaPlate(
                    czb_id_id=czb_id_model.id,
                    rna_plate_id=rna_plate_model.id,
                    well_id=well_id,
                )
            )


class RemoteNewInternalCZBIDPopulator(
    RemoteWorksheetPopulatorMixin, NewInternalCZBIDPopulator
):
    """
    This class popoulates any missing czb_ids from the mega og_plates.xlsx sheet that
    were cherry picked from downstairs. This is only relevant for new cherry picked
    internal samples which are added directly to og_plates.xlsx. In the future the
    appscripts should write directly to the database and this populator will not be
    needed.
    """

    @property
    def spreadsheet_id_config_key(self) -> str:
        return "og_plates_megasheet_sheet_id"

    @property
    def sheet_name(self) -> str:
        return "Sheet1"
