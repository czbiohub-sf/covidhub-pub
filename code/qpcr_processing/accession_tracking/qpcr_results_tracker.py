import csv
import logging
from datetime import datetime

from pytz import timezone

from covidhub.google import drive

logger = logging.getLogger(__name__)


class PCRResultsTracker:
    """
    Class that tracks a qPCR barcode through our system. If it's been processed it also grabs and
    stores the results for easy lookup.

    Parameters
    ----------
    pcr_barcode:
        The pcr barcode to track
    sample_barcode:
        The 96 sample plate associated with the run.
    results_folder_id:
        Location of processing results in drive
    drive_service:
        Authenticated drive service to query with
    completed_pcr_barcodes:
        List of already processed pcr_barcodes
    """

    def __init__(
        self,
        pcr_barcode,
        sample_barcode,
        results_folder_id,
        drive_service,
        completed_pcr_barcodes,
    ):

        self.pcr_barcode = pcr_barcode
        self.sample_barcode = sample_barcode
        self.results_filename = "{}-{}-results.csv".format(
            self.sample_barcode, self.pcr_barcode
        )
        self.results_folder_id = results_folder_id
        self.drive_service = drive_service
        self.completed_pcr_barcodes = completed_pcr_barcodes
        self.qPCR_processing_complete = False
        self.qPCR_processed_timestamp = ""
        self.resulted_to_cb = ""
        self.calls = None
        self.resulted_to_cb_timestamp = ""

        self.set_qPCR_processing_complete()
        if self.qPCR_processing_complete:
            self.set_qPCR_processed_timestamp()
            self.set_calls()

    def set_calls(self):
        """
        Grabs the associated results.csv and stores accession data
        """
        if self.qPCR_processing_complete:
            # If processing complete get results file
            with drive.get_file_by_name(
                self.drive_service,
                self.results_folder_id,
                self.results_filename,
                drive.FindMode.MOST_RECENTLY_MODIFIED,
            ) as fh:
                self.calls = PCRResultsTracker.get_accession_to_call_mapping_from_results_csv(
                    fh
                )
        if self.calls:
            logger.info(f"Found results file: {self.results_filename}")

    def set_qPCR_processed_timestamp(self):
        """Extract the processed time from the results file timestamp"""
        if self.qPCR_processing_complete:
            file = drive.find_file_by_name(
                self.drive_service,
                self.results_folder_id,
                self.results_filename,
                drive.FindMode.MOST_RECENTLY_MODIFIED,
            )
            time_str = file.modifiedTime
            # gdrive saving these files as UTC need to convert
            date_utc = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%f%z")
            pst_date = date_utc.astimezone(timezone("US/Pacific"))
            pst_date.strftime("%m/%d/%Y, %H:%M:%S")
            self.qPCR_processed_timestamp = pst_date.strftime("%m/%d/%Y, %H:%M:%S")

    def get_call(self, accession):
        """
        Given an accession return the call made from the processed qPPCR results
        """
        accession = accession.rstrip()
        if not self.calls:
            return ""
        elif accession not in self.calls.keys():
            return ""
        return self.calls[accession]["call"]

    def get_gene_ct(self, accession, gene):
        """
        Given a gene and accession value return the ct amount seen.
        """
        if not self.calls or accession not in self.calls.keys():
            return ""
        accession_data = self.calls[accession]
        gene_key = f"{gene} Ct"
        if gene_key not in accession_data.keys():
            return ""
        return accession_data[gene_key]

    def set_qPCR_processing_complete(self):
        """
        Checks if qPCR processing is complete by looking in "completed" marker file list.
        """
        if self.pcr_barcode == "":
            raise ValueError(
                f"Sample {self.sample_barcode} does not have pcr_barcode match"
            )
        self.qPCR_processing_complete = self.pcr_barcode in self.completed_pcr_barcodes

    @staticmethod
    def get_accession_to_call_mapping_from_results_csv(fh):
        """
        Converts a results.csv to a mapping from {accession: call, ct_info_per_gene}
        """
        results = {}
        HEADER = 0
        PLATE_MAP = 1
        RESULTS = 2
        reader = csv.reader(fh)
        reading = HEADER
        for row in reader:
            if len(row) == 0:
                continue
            if reading == HEADER:
                if row[0] == "Controls":
                    reading = PLATE_MAP
            elif reading == PLATE_MAP:
                if row[0] == "H":
                    reading = RESULTS
            elif reading == RESULTS:
                if row[0] == "Well":
                    # set row header
                    genes_names = row[3:]
                else:
                    row_info = {
                        "call": row[2],
                    }
                    gene_cts = row[3:]
                    gene_values = {g: v for g, v in zip(genes_names, gene_cts)}
                    row_info.update(gene_values)
                    accession = row[1]
                    results[accession.rstrip()] = row_info
        return results
