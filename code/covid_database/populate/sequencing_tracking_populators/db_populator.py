import logging

import covidhub.google.drive as drive
from covid_database import session_scope
from covid_database.populate.sequencing_tracking_populators.external_metadata_populator import (
    ExternalMetadataPopulator,
)
from covid_database.populate.sequencing_tracking_populators.legacy_external_metadata_populator import (
    LegacyExternalMetadataPopulator,
)
from covid_database.populate.sequencing_tracking_populators.legacy_internal_samples_populator import (
    LegacyInternalSamplesPopulator,
)
from covid_database.populate.sequencing_tracking_populators.library_plates_populator import (
    LibraryPlatePopulator,
)
from covid_database.populate.sequencing_tracking_populators.new_internal_czb_ids_populator import (
    RemoteNewInternalCZBIDPopulator,
)
from covid_database.populate.sequencing_tracking_populators.og_plate_metadata_populator import (
    OGPlateMetadataPopulator,
)
from covid_database.populate.sequencing_tracking_populators.projects_populator import (
    RemoteProjectsPopulator,
)
from covid_database.populate.sequencing_tracking_populators.sequencing_plate_populator import (
    RemoteSequencingPlatesPopulator,
)
from covid_database.populate.sequencing_tracking_populators.working_plates_populator import (
    CZBIDToWorkingPlatePopulator,
    RemoteWorkingPlatesPopulator,
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
            RemoteProjectsPopulator,
            LegacyExternalMetadataPopulator,
            ExternalMetadataPopulator,
            LegacyInternalSamplesPopulator,
            OGPlateMetadataPopulator,
            RemoteNewInternalCZBIDPopulator,
            RemoteWorkingPlatesPopulator,
            CZBIDToWorkingPlatePopulator,
            LibraryPlatePopulator,
            RemoteSequencingPlatesPopulator,
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
                populator.populate_models()
