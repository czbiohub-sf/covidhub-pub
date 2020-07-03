from __future__ import annotations

import csv
import logging
import re
from typing import Dict, Optional, TextIO

import dateutil

from covidhub.config import Config
from covidhub.constants import Call, COLS_96, ControlType, ROWS_96, VALID_ACCESSION
from covidhub.google import drive
from qpcr_processing.metadata import BravoMetadata
from qpcr_processing.protocol import Protocol
from qpcr_processing.well_results import WellResults

logger = logging.getLogger(__name__)


class ProcessingResults:
    """
    Class that holds processing data needed for all our various output files
    """

    def __init__(
        self,
        bravo_metadata: BravoMetadata,
        protocol: Protocol,
        completion_time: str,
        controls: str,
        well_to_results_mapping: Dict[str, WellResults],
        *,
        quant_amp_data: Optional[Dict] = None,
    ):
        self.bravo_metadata = bravo_metadata

        logger.debug(f"Initializing processing results for {self.combined_barcode}")

        self.protocol = protocol
        self.completion_time = completion_time
        self.controls = controls
        self.well_results: Dict[str, WellResults] = well_to_results_mapping
        self.quant_amp_data = quant_amp_data

    @property
    def combined_barcode(self):
        return f"{self.bravo_metadata.sample_barcode}-{self.bravo_metadata.pcr_barcode}"

    @property
    def experimental_run(self):
        return self.bravo_metadata.experimental_run | self.protocol.experimental

    @property
    def results_filename(self):
        return f"{self.combined_barcode}-results.csv"

    @property
    def final_pdf_filename(self):
        return f"{self.combined_barcode}_final.pdf"

    @property
    def cb_report_filename(self):
        return f"{self.combined_barcode}_cb_results.csv"

    def invalid_accessions(self):
        """Make sure all accessions match the VALID_ACCESSION regex"""
        for well_id, well_result in self.well_results.items():
            if well_result.accession and well_result.control_type is None:
                if re.fullmatch(VALID_ACCESSION, well_result.accession) is None:
                    logger.critical(
                        f"{self.combined_barcode} has an invalid accession in "
                        f"{well_id}: '{well_result.accession}'",
                        extra={"notify_slack": True},
                    )
                    return True

        return False

    def get_well_results(self, well: str) -> WellResults:
        """Return the processing results for the given well"""
        return self.well_results[well]

    @property
    def formatted_metadata(self):
        """Return the metadata of the processing results as a dict"""
        return {
            "Sample Plate Barcode": self.bravo_metadata.sample_barcode,
            "RNA Plate Barcode": self.bravo_metadata.rna_barcode,
            "PCR Plate Barcode": self.bravo_metadata.pcr_barcode,
            "Completion Time": self.completion_time,
            "Researcher": self.bravo_metadata.researcher,
            "Bravo Station ID": self.bravo_metadata.bravo_station,
            "qPCR Station ID": self.bravo_metadata.qpcr_station,
            "Controls": self.controls,
        }

    def get_formatted_run_data(self, include_cluster_warnings=False):
        """Format the processing results as a list of rows"""
        clean_results = []
        # Add the run data
        for well, well_result in self.well_results.items():
            row = [well, *well_result.format_row()]
            if include_cluster_warnings:
                if well_result.call.possible_cluster:
                    row.append(f"{well_result.call}")
            clean_results.append(row)
        return clean_results

    def add_metadata_to_file(self, fh, metadata):
        """Add the metadata info to the open file"""
        for label, value in metadata.items():
            fh.write(f"{label},{value}\n")
        fh.write("\n")

    def add_plate_map_to_file(self, fh):
        """Add the plate map info to the open file"""

        # Add the platelayout data
        print(",{}".format(",".join(str(c) for c in COLS_96)), file=fh)

        # make plate map
        for row in ROWS_96:
            print(
                "{},{}".format(
                    row,
                    ",".join(str(self.well_results[f"{row}{col}"]) for col in COLS_96),
                ),
                file=fh,
            )

        print(file=fh)

    def add_run_data_to_file(self, fh, include_cluster_warnings):
        """Add main processing results as a table to the open file"""
        # Add the run data
        fh.write(",".join(self.protocol.formatted_row_header) + "\n")
        formatted_run_data = self.get_formatted_run_data(include_cluster_warnings)
        for clean_result in formatted_run_data:
            fh.write(",".join([str(e) for e in clean_result]) + "\n")

    def write_cb_report(self, fh):
        logger.info(
            msg=f"Writing results data for: {self.combined_barcode} to: {fh.name}"
        )
        self.add_metadata_to_file(fh, self.formatted_metadata_cb_results)
        # Add the run data
        self.add_run_data_to_file(fh, True)

    @property
    def station_id(self):
        if self.bravo_metadata.qpcr_station:
            return self.bravo_metadata.qpcr_station[-1]
        else:
            return ""

    @property
    def formatted_metadata_cb_results(self):
        """Return the metadata of the processing results as a dict"""
        return {
            "Sample Plate Barcode": self.bravo_metadata.sample_barcode,
            "RNA Plate Barcode": self.bravo_metadata.rna_barcode,
            "PCR Plate Barcode": self.bravo_metadata.pcr_barcode,
            "Completion Time": self.completion_time,
            "Researcher": self.bravo_metadata.researcher,
            "Station ID": self.station_id,
            "Controls": self.controls,
            "Testing Location": "CZ Biohub",
        }

    def write_results(self, fh):
        logger.info(
            msg=f"Writing results data for: {self.combined_barcode} to: {fh.name}"
        )
        # Add the metadata
        self.add_metadata_to_file(fh, self.formatted_metadata)
        # Add the platelayout data
        self.add_plate_map_to_file(fh)
        # Add the run data
        self.add_run_data_to_file(fh, False)

    def write_marker_file(self, drive_service, markers_folder_id):
        """Writes a marker file for the given results"""
        with drive.put_file(
            drive_service, markers_folder_id, self.bravo_metadata.pcr_barcode
        ):
            ...

    @staticmethod
    def format_time(timestamp: str, cfg: Config) -> str:
        """helper function to reformat UTC timestamp to the configured timezone"""
        # get timezone from config, use UTC if unavailable
        timezone = dateutil.tz.gettz(
            cfg["GENERAL"].get("timezone", "America/Los Angeles")
        )

        # parse UTC timestamp and convert to timezone
        dt = dateutil.parser.parse(timestamp).astimezone(timezone)

        # format as desired
        return dt.strftime("%Y-%m-%d %H:%M:%S %Z")

    @staticmethod
    def from_results_file_in_drive(
        drive_service, protocol, cfg, results_folder_id, filename
    ):
        """Initialize processing results from just the name of the results file in drive"""
        with drive.get_file_by_name(
            drive_service,
            results_folder_id,
            filename,
            drive.FindMode.MOST_RECENTLY_MODIFIED,
        ) as fh:
            ProcessingResults.from_results_file(fh=fh, protocol=protocol)

    @staticmethod
    def from_results_data(
        cfg: Config,
        well_to_results_mapping: Dict[str, WellResults],
        protocol: Protocol,
        run_ended: str,
        bravo_metadata: BravoMetadata,
        quant_amp_data: Dict,
    ) -> ProcessingResults:
        """
        Create a ProcessingResults object from a results dictionary

        Parameters
        ----------
        cfg :
            a Config instance
        well_to_results_mapping :
            results information in a dictionary {well: WellResults}
        protocol :
            The protocol used for processing
        run_ended :
            Timestamp from the Run Information file, which is MM/DD/YYYY and UTC time
        bravo_metadata :
            The bravo metadata for the run
        quant_amp_data :
            Dictionary of pd.DataFrame objects for each fluor containing Ct values

        Returns
        -------
        ProcessingResults
            The resulting ProcessingResults object.
        """
        controls_status = "Failed"
        if all(
            res.call == Call.PASS
            for res in well_to_results_mapping.values()
            if res.control_type is not None
        ):
            controls_status = "Passed"

        run_ended = ProcessingResults.format_time(run_ended, cfg)

        # check for contaminated positives. SOP V2 will only check the neighbors. SOP V3
        # also checks distant wells with a higher cutoff
        protocol.flag_contamination(well_to_results_mapping)

        return ProcessingResults(
            protocol=protocol,
            bravo_metadata=bravo_metadata,
            completion_time=run_ended,
            controls=controls_status,
            well_to_results_mapping=well_to_results_mapping,
            quant_amp_data=quant_amp_data,
        )

    @staticmethod
    def from_results_file(fh: TextIO, protocol: Protocol):
        """
        Instantiate a ProcessingResults object from a results.csv file
        """
        HEADER = 0
        PLATE_MAP = 1
        RESULTS = 2
        reader = csv.reader(fh)
        reading = HEADER
        rna_barcode = None
        sample_plate_barcode = None
        completion_time = None
        pcr_barcode = None
        researcher = None
        bravo_station = None
        qpcr_station = None
        controls = None
        well_to_results_mapping: Dict[str, WellResults] = {}

        for row in reader:
            if len(row) == 0:
                continue
            if reading == HEADER:
                if row[0] == "Sample Plate Barcode":
                    sample_plate_barcode = row[1]
                elif row[0] == "RNA Plate Barcode":
                    rna_barcode = row[1]
                elif row[0] == "PCR Plate Barcode":
                    pcr_barcode = row[1]
                elif row[0] == "Completion Time":
                    completion_time = row[1]
                elif row[0] == "Researcher":
                    researcher = row[1]
                elif row[0] == "Bravo Station ID":
                    bravo_station = row[1]
                elif row[0] == "qPCR Station ID":
                    qpcr_station = row[1]
                elif row[0] == "Station ID":
                    bravo_station = f"clia-bravo-{row[1]}"
                    qpcr_station = f"clia-pcr-{row[1]}"
                elif row[0] == "Controls":
                    controls = row[1]
                    reading = PLATE_MAP
            elif reading == PLATE_MAP:
                if row[0] == "":
                    continue
                elif row[0] == "H" or row[0] == "Well":
                    reading = RESULTS
            elif reading == RESULTS:
                if row[0] == "Well":
                    continue
                else:
                    well = row[0]
                    accession = row[1]
                    gene_cts = row[3:]
                    gene_values = {
                        g: float(v) if v != "" else float("NaN")
                        for g, v in zip(protocol.gene_list, gene_cts)
                    }

                    control_type = ControlType.parse_control(accession)

                    if control_type:
                        call = protocol.check_control(gene_values, control_type)
                    else:
                        call = protocol.call_well(gene_values)

                    well_to_results_mapping[well] = WellResults(
                        accession=accession, call=call, gene_cts=gene_values
                    )

        protocol.flag_contamination(well_to_results_mapping)

        bravo_metadata = BravoMetadata(
            pcr_barcode=pcr_barcode,
            rna_barcode=rna_barcode,
            sample_barcode=sample_plate_barcode,
            researcher=researcher,
            bravo_station=bravo_station,
            qpcr_station=qpcr_station,
        )

        return ProcessingResults(
            bravo_metadata=bravo_metadata,
            protocol=protocol,
            completion_time=completion_time,
            controls=controls,
            well_to_results_mapping=well_to_results_mapping,
        )
