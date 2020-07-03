import logging

import covidhub.google.drive as drive
from covid_database import session_scope
from covid_database.populate.qpcr_processing_populators.accession_locations_populator import (
    AccessionLocationsPopulator,
)
from covid_database.populate.qpcr_processing_populators.form_choices_populator import (
    RemoteFormChoicesPopulator,
)
from covid_database.populate.qpcr_processing_populators.freezer_checkin_populator import (
    RemoteFreezerCheckinPopulator,
)
from covid_database.populate.qpcr_processing_populators.freezer_checkout_populator import (
    RemoteFreezerCheckoutPopulator,
)
from covid_database.populate.qpcr_processing_populators.fridge_checkin_populator import (
    RemoteFridgeCheckinPopulator,
)
from covid_database.populate.qpcr_processing_populators.personnel_populator import (
    RemotePersonnelPopulator,
)
from covid_database.populate.qpcr_processing_populators.plate_layout_populator import (
    PlateLayoutPopulator,
)
from covid_database.populate.qpcr_processing_populators.qpcr_results_populator import (
    QPCRResultsPopulator,
)
from covid_database.populate.qpcr_processing_populators.qpcr_run_populator import (
    RemoteQPCRRunPopulator,
)
from covid_database.populate.qpcr_processing_populators.reagent_populator import (
    ReagentPopulator,
    RemoteReagentPrepPopulator,
)
from covid_database.populate.qpcr_processing_populators.rna_extraction_populator import (
    RemoteRNAExtractionPopulator,
)
from covid_database.populate.qpcr_processing_populators.rna_rerun_populator import (
    RemoteRNARerunPopulator,
)
from covid_database.populate.qpcr_processing_populators.sample_registration_populator import (
    RemoteSamplePlateMetadataPopulator,
    RemoteSampleRegistrationPopulator,
)
from covid_database.populate.qpcr_processing_populators.waste_management_populator import (
    RemoteWasteManagementPopulator,
)

log = logging.getLogger(__name__)


class DBPopulator:
    """
    Class that defines the order of populators to call and populates all data from drive.

    Parameters
    ----------
    :param config: Config instance
    :param google_credentials: google credentials to use
    """

    def __init__(self, google_credentials, config):
        self.drive_service = drive.get_service(google_credentials)
        self.config = config

    @property
    def populator_order(self):
        """Order of populators to call"""
        return [
            RemoteFormChoicesPopulator,
            RemotePersonnelPopulator,
            ReagentPopulator,
            RemoteReagentPrepPopulator,
            RemoteSampleRegistrationPopulator,
            RemoteSamplePlateMetadataPopulator,
            PlateLayoutPopulator,
            AccessionLocationsPopulator,
            RemoteFridgeCheckinPopulator,
            RemoteRNAExtractionPopulator,
            RemoteRNARerunPopulator,
            RemoteQPCRRunPopulator,
            QPCRResultsPopulator,
            RemoteWasteManagementPopulator,
            RemoteFreezerCheckinPopulator,
            RemoteFreezerCheckoutPopulator,
        ]

    def populate_all_data(self):
        """Runs through each class in self.populator_order and calls their
        populate_models() method.
        """
        log.info("Populating all data")
        with session_scope() as session:
            for populator_class in self.populator_order:
                populator = populator_class(
                    session=session, drive_service=self.drive_service, cfg=self.config
                )
                try:
                    populator.populate_models()
                except Exception as e:
                    log.critical(
                        f"Exception in {populator_class.__name__}: {e}",
                        extra={"notify_slack": True},
                    )
                    raise
