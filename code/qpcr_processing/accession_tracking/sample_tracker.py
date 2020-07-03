import logging
from typing import List

import pandas as pd

from qpcr_processing.accession_tracking.accession_tracking_data_store import (
    ProcessingResources,
)
from qpcr_processing.accession_tracking.qpcr_results_tracker import PCRResultsTracker

logger = logging.getLogger(__name__)


class SampleTracker:
    """
    Class that tracks a 96 sample plate barcode through our system.

    Parameters
    ----------
    timestamp: str
        Timestamp from WellLit File
    form_data: FormData
        Initialized form data as pd.DataFrames for easy lookups
    results_folder_id:
        Location of processing results in drive
    drive_service:
        Authenticated drive service to query with
    sample_barcode:
        The 96 sample plate barcode.
    completed_pcr_barcodes:
        List of already processed pcr_barcodes
    accession_locations:
        Mapping from accession IDs to locations
    """

    def __init__(
        self,
        timestamp,
        drive_service,
        sample_barcode,
        processing_resources: ProcessingResources,
    ):
        self.timestamp = timestamp
        self.sample_barcode = sample_barcode
        self.completed_pcr_barcodes = processing_resources.completed_pcr_barcodes
        self.results_folder_id = processing_resources.results_folder_id
        self.drive_service = drive_service
        self.processing_resources = processing_resources
        self.accession_locations = processing_resources.accession_locations
        self.mark_as_processed_sample_barcodes = (
            processing_resources.mark_as_processed_sample_barcodes
        )

        self.rna_plate_barcode = ""
        self.registered = False
        self.registered_column_index = 0
        self.registered_time = ""
        self.checked_into_fridge = False
        self.checked_into_freezer = False
        self.started_rna_extractions = False
        self.registered_by = ""
        self.registration_notes = ""
        self.checked_into_fridge = False
        self.checked_into_fridge_location = ""
        self.checked_into_freezer = False
        self.started_rna_extractions = False
        self.started_rna_extractions_by = ""
        self.started_rna_extractions_time = ""
        self.completed_rna_extractions = False
        self.qpcr_results = []
        logger.info(
            msg=f"Initializing data for " f"Sample Plate Barcode: {self.sample_barcode}"
        )
        try:
            self.set_registered()
            if self.registered:
                self.set_registered_time()
                self.set_registered_by()
                self.set_registration_notes()
            self.set_checked_into_fridge()
            if self.checked_into_fridge:
                self.set_checked_into_fridge_location()
            self.set_checked_into_freezer()
            self.set_started_rna_extractions()
            if self.started_rna_extractions:
                self.set_started_rna_extractions_by()
                self.set_started_rna_extractions_time()
                self.set_completed_rna_extractions()
            if self.completed_rna_extractions:
                self.set_rna_plate_barcode()
                self.set_qpcr_results()
        except Exception:
            logger.exception(msg="Error in getting accession data.")

    def set_registered(self):
        """Check if the given sample has been registered with the Sample Registration form"""
        barcodes = list(
            self.processing_resources.registered_df["sample_plate_barcode_1"].values
        )
        if self.sample_barcode in barcodes:
            self.registered = True
            return
        for i in range(2, 11):
            extra_values = self.processing_resources.registered_df[
                f"sample_plate_barcode_{i}"
            ].values
            extra_values = [x for x in extra_values if x]
            if self.sample_barcode in extra_values:
                self.registered_column_index = i
                self.registered = True
                return
        return

    def set_registered_time(self):
        """Get the time the sample was registered"""
        if self.registered:
            column_name = "sample_plate_barcode_1"
            if self.registered_column_index != 0:
                column_name = f"sample_plate_barcode_{self.registered_column_index}"
            registered_time = self.processing_resources.registered_df.loc[
                self.processing_resources.registered_df[column_name]
                == self.sample_barcode
            ]["timestamp"].values[0]
            self.registered_time = pd.to_datetime(str(registered_time)).strftime(
                "%Y%m%d %H:%M:%S"
            )

    def set_registered_by(self):
        """Get the researcher the sample was registered by"""
        if self.registered:
            column_name = "sample_plate_barcode_1"
            if self.registered_column_index != 0:
                column_name = f"sample_plate_barcode_{self.registered_column_index}"
            self.registered_by = self.processing_resources.registered_df.loc[
                self.processing_resources.registered_df[column_name]
                == self.sample_barcode
            ]["researcher_name"].values[0]

    def set_registration_notes(self):
        """Get the registration notes for the sample"""
        if self.registered:
            column_name = "sample_plate_barcode_1"
            if self.registered_column_index != 0:
                column_name = f"sample_plate_barcode_{self.registered_column_index}"
            self.registration_notes = self.processing_resources.registered_df.loc[
                self.processing_resources.registered_df[column_name]
                == self.sample_barcode
            ]["notes"].values[0]

    def set_checked_into_fridge(self):
        """Check if the given sample has been checked in with the 4C check in form"""
        self.checked_into_fridge = (
            self.sample_barcode
            in self.processing_resources.check_in_df["sample_plate_barcode"].values
        )

    def set_checked_into_fridge_location(self):
        """Return the shelf, rack and plate the sample was checked into"""
        shelf = self.processing_resources.check_in_df.loc[
            self.processing_resources.check_in_df["sample_plate_barcode"]
            == self.sample_barcode
        ]["shelf"].values[0]
        rack = self.processing_resources.check_in_df.loc[
            self.processing_resources.check_in_df["sample_plate_barcode"]
            == self.sample_barcode
        ]["rack"].values[0]
        plate = self.processing_resources.check_in_df.loc[
            self.processing_resources.check_in_df["sample_plate_barcode"]
            == self.sample_barcode
        ]["plate"].values[0]
        self.checked_into_fridge_location = (
            f"shelf: {shelf}, rack: {rack}, plate: {plate}"
        )

    def set_checked_into_freezer(self):
        """Check if the given sample has been checked into the freezer with the minus80
        Checkin form"""
        self.checked_into_freezer = (
            self.sample_barcode
            in self.processing_resources.freezer_check_in_df[
                "sample_plate_barcode"
            ].values
        )

    def set_started_rna_extractions(self):
        """Check if the given sample has started RNA extractions with the Starting Bravo form"""
        self.started_rna_extractions = (
            self.sample_barcode
            in self.processing_resources.starting_bravo_df[
                "sample_plate_barcode"
            ].values
        )

    def set_started_rna_extractions_by(self):
        """Check if the given sample has started RNA extractions with the Starting Bravo form"""
        started_rna_extractions_by_values = self.processing_resources.starting_bravo_df.loc[
            self.processing_resources.starting_bravo_df["sample_plate_barcode"]
            == self.sample_barcode
        ][
            "researcher_name"
        ].values
        self.started_rna_extractions_by = ", ".join(started_rna_extractions_by_values)

    def set_started_rna_extractions_time(self):
        """Check if the given sample has started RNA extractions with the Starting Bravo form"""
        started_rna_extractions_time_values = self.processing_resources.starting_bravo_df.loc[
            self.processing_resources.starting_bravo_df["sample_plate_barcode"]
            == self.sample_barcode
        ][
            "timestamp"
        ].values
        converted_times = [
            pd.to_datetime(str(time)).strftime("%Y%m%d %H:%M:%S")
            for time in started_rna_extractions_time_values
        ]
        self.started_rna_extractions_time = ", ".join(converted_times)

    def set_completed_rna_extractions(self):
        """Check if the given sample has finished RNA extractions with the
        Bravo RNA extractions form"""
        self.completed_rna_extractions = (
            self.sample_barcode
            in self.processing_resources.bravo_rna_df["sample_plate_barcode"].values
        )

    def set_rna_plate_barcode(self):
        """Get 96 RNA plate barcode from Bravo RNA form"""
        self.rna_plate_barcode = self.processing_resources.bravo_rna_df.loc[
            self.processing_resources.bravo_rna_df["sample_plate_barcode"]
            == self.sample_barcode
        ]["rna_plate_barcode"].values[0]

    def set_qpcr_results(self):
        """
        Check for qPCR barcodes for the given sample with the Bravo RNA extractions form. If found
        initialize a PCRResultsTracker for each.
        """
        pcr_barcodes = self.processing_resources.bravo_rna_df.loc[
            self.processing_resources.bravo_rna_df["sample_plate_barcode"]
            == self.sample_barcode
        ]["qpcr_plate_barcode"].values
        for pcr_barcode in pcr_barcodes:
            pcr_results_tracker = PCRResultsTracker(
                pcr_barcode=pcr_barcode,
                sample_barcode=self.sample_barcode,
                results_folder_id=self.results_folder_id,
                drive_service=self.drive_service,
                completed_pcr_barcodes=self.completed_pcr_barcodes,
            )
            self.qpcr_results.append(pcr_results_tracker)

    @property
    def been_rerun(self):
        """Return if the given sample has been rerun"""
        return self.qpcr_results > 1

    @property
    def ready_for_rna_extractions(self):
        if self.sample_barcode in self.mark_as_processed_sample_barcodes:
            return False
        return (
            self.registered
            and self.checked_into_fridge
            and not self.started_rna_extractions
        )

    @property
    def finished_processing(self):
        """Return True if every pcr barcode for this sample has completed processing"""
        if self.completed_rna_extractions:
            if len(self.qpcr_results) == 0:
                return False
            for qpcr_result in self.qpcr_results:
                if not qpcr_result.qPCR_processing_complete:
                    return False
            return True
        return False

    def get_accession_location(self, accession):
        return self.accession_locations.get(accession, ("", ""))

    def format_row_entry_for_supervisor_plate_queue(self) -> List[List]:
        """
        Format the row info needed for the supervisor plate queue sheet for the given sample
        """
        plate_queue_row = [
            self.sample_barcode,
            self.registered_time,
            self.registered_by,
            self.checked_into_fridge_location,
            self.registration_notes,
            self.ready_for_rna_extractions,
            self.started_rna_extractions_time,
            self.started_rna_extractions_by,
        ]
        return plate_queue_row

    def format_verbose_row_entries(self, well, accession) -> List[List]:
        """
        Given well and accession values generate the appropriate row entries for the verbose acession tracking
        csv. If a sample was rerun multiple rows are returned each with a different qPCR barcode.
        """
        results = []
        verbose_sample_row_start = [
            self.timestamp,
            self.sample_barcode,
            self.rna_plate_barcode,
            self.get_accession_location(accession)[0],
            self.get_accession_location(accession)[1],
            well,
            accession,
            self.registered,
            self.checked_into_fridge,
            self.started_rna_extractions,
            self.checked_into_freezer,
            self.completed_rna_extractions,
        ]
        if len(self.qpcr_results) == 0:
            results.append(
                verbose_sample_row_start + ["", "", False, "", "", "", "", ""]
            )
        else:
            for qpcr_result in self.qpcr_results:
                results.append(
                    verbose_sample_row_start
                    + [
                        qpcr_result.pcr_barcode,
                        qpcr_result.get_call(accession),
                        qpcr_result.qPCR_processing_complete,
                        qpcr_result.get_gene_ct(accession, "E"),
                        qpcr_result.get_gene_ct(accession, "N"),
                        qpcr_result.get_gene_ct(accession, "RdRp"),
                        qpcr_result.get_gene_ct(accession, "RNAse P"),
                        qpcr_result.resulted_to_cb,
                    ]
                )
        return results

    def format_row_entries_clin_lab(self, well, accession) -> List[List]:
        """
        Given well and accession values generate the appropriate row entries for the clin lab reporting
        csv. If a sample was rerun multiple rows are returned each with a different qPCR barcode.
        """
        results = []
        clin_lab_sample_row_start = [
            self.registered_time,
            self.sample_barcode,
            well,
            accession,
            self.registered,
            self.started_rna_extractions,
        ]
        if len(self.qpcr_results) == 0:
            results.append(clin_lab_sample_row_start + ["", "", ""])
        else:
            for qpcr_result in self.qpcr_results:
                results.append(
                    clin_lab_sample_row_start
                    + [
                        qpcr_result.pcr_barcode,
                        qpcr_result.qPCR_processing_complete,
                        qpcr_result.qPCR_processed_timestamp,
                    ]
                )
        return results
