from __future__ import annotations

import html
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Optional

import pandas as pd

from covidhub.collective_form import clean_single_row, CollectiveForm
from covidhub.constants import Fluor, SamplePlateType, SOP_EXTRACTIONS
from covidhub.constants.enums import ControlsMappingType
from covidhub.constants.qpcr_forms import (
    Base,
    BravoRNAExtraction,
    BravoStart,
    QPCRMetadata,
    RNARerun,
    SampleMetadata,
)
from covidhub.error import MetadataNotFoundError, MismatchError
from qpcr_processing.protocol import Protocol

logger = logging.getLogger(__name__)


class ReportNote:
    def __init__(
        self, body: str = None, timestamp: str = None, researcher: str = None,
    ):
        self.body = body
        self.timestamp = timestamp
        self.researcher = researcher

    def __str__(self):
        return f"{self.researcher}; {self.timestamp}; {self.body}"

    def to_html(self) -> str:
        """Return a HTML sequence representing this ReportNote."""
        researcher = html.escape(self.researcher)
        timestamp = html.escape(str(self.timestamp))
        body = html.escape(self.body)
        return f"<b>{researcher} [{timestamp}]:</b> {body}"


@dataclass
class BravoMetadata:
    pcr_barcode: str
    rna_barcode: str = "MISSING"
    sample_barcode: str = "MISSING"
    researcher: str = "MISSING"
    extraction_version: str = "MISSING"
    sample_type: SamplePlateType = None
    experimental_run: bool = True
    controls_type: ControlsMappingType = None
    bravo_rerun_notes: Optional[ReportNote] = None
    bravo_rna_notes: Optional[ReportNote] = None
    bravo_station: Optional[str] = None
    rna_description: Optional[str] = None
    qpcr_description: Optional[str] = None
    sample_source: Optional[str] = None
    qpcr_notes: Optional[ReportNote] = None
    qpcr_station: Optional[str] = None
    sample_plate_metadata_notes: Optional[ReportNote] = None
    sop_protocol: Optional[str] = None
    starting_bravo_notes: Optional[ReportNote] = None

    @classmethod
    def load_from_spreadsheet(
        cls, pcr_barcode: str, collective_form: CollectiveForm
    ) -> BravoMetadata:
        instance = cls(pcr_barcode)

        logger.info(
            msg=f"Initializing Bravo metadata for PCR Plate Barcode: {pcr_barcode}"
        )

        if collective_form is not None:
            instance._parse(collective_form)

        return instance

    def _parse(self, collective_form: CollectiveForm):
        bravo_rna = collective_form[BravoRNAExtraction.SHEET_NAME]
        bravo_rerun = collective_form[RNARerun.SHEET_NAME]
        qpcr_metadata = collective_form[QPCRMetadata.SHEET_NAME]
        sample_metadata = collective_form[SampleMetadata.SHEET_NAME]
        starting_bravo = collective_form[BravoStart.SHEET_NAME]

        try:
            row = clean_single_row(
                bravo_rna, BravoRNAExtraction.QPCR_PLATE_BARCODE, self.pcr_barcode,
            )
        except MetadataNotFoundError:
            rerun_row = clean_single_row(
                bravo_rerun, RNARerun.QPCR_PLATE_BARCODE, self.pcr_barcode,
            )

            rna_barcode = rerun_row[RNARerun.RNA_PLATE_BARCODE]
            self.bravo_rerun_notes = self._format_sheet_note(rerun_row)

            row = clean_single_row(bravo_rna, RNARerun.RNA_PLATE_BARCODE, rna_barcode,)

        self.rna_barcode = row[BravoRNAExtraction.RNA_PLATE_BARCODE]
        self.sample_barcode = row[BravoRNAExtraction.SAMPLE_PLATE_BARCODE]
        self.researcher = row[BravoRNAExtraction.CLIAHUB_RESEARCHER]
        self.bravo_station = row[BravoRNAExtraction.BRAVO_STATION]
        self.bravo_rna_notes = self._format_sheet_note(row)

        try:
            sample_metadata_row = clean_single_row(
                sample_metadata,
                SampleMetadata.SAMPLE_PLATE_BARCODE,
                self.sample_barcode,
            )
        except MetadataNotFoundError:
            ...
        else:
            self.sample_type = SamplePlateType(
                sample_metadata_row[SampleMetadata.SAMPLE_TYPE]
            )
            self.experimental_run = self.sample_type != SamplePlateType.ORIGINAL

            self.sample_plate_metadata_notes = self._format_sheet_note(
                sample_metadata_row
            )
            self.controls_type = ControlsMappingType(
                sample_metadata_row[SampleMetadata.CONTROLS_TYPE]
            )

            self.sample_source = sample_metadata_row[SampleMetadata.SAMPLE_SOURCE]

        try:
            starting_bravo_row = clean_single_row(
                starting_bravo,
                BravoStart.SAMPLE_PLATE_BARCODE,
                self.sample_barcode,
                -1,
            )
        except MetadataNotFoundError:
            ...
        else:
            bravo_sample_type = SamplePlateType(
                starting_bravo_row[BravoStart.SAMPLE_TYPE]
            )
            self.experimental_run |= bravo_sample_type != SamplePlateType.ORIGINAL

            self.extraction_version = starting_bravo_row[BravoStart.EXTRACTION_VERSION]
            self.experimental_run |= self.extraction_version not in SOP_EXTRACTIONS

            self.rna_description = starting_bravo_row[BravoStart.DESCRIPTION]
            self.starting_bravo_notes = self._format_sheet_note(starting_bravo_row)

        self._parse_qpcr_metadata(qpcr_metadata)

        logger.info(
            msg=f"Parsed metadata - "
            f"RNA Barcode: {self.rna_barcode}, "
            f"Sample Barcode: {self.sample_barcode}, "
            f"Researcher ID: {self.researcher}, "
            f"Extraction version: {self.extraction_version}, "
            f"Sample Type: {self.sample_type}, "
            f"Experimental Run: {self.experimental_run}, "
            f"Bravo Station ID: {self.bravo_station}, "
            f"qPCR Station ID: {self.qpcr_station}, "
            f"Sample Plate Metadata notes: {self.sample_plate_metadata_notes}, "
            f"Starting Bravo notes: {self.starting_bravo_notes}, "
            f"Extraction description: {self.rna_description}, "
            f"Bravo RNA notes: {self.bravo_rna_notes}, "
            f"qPCR notes: {self.qpcr_notes}, "
            f"qPCR description: {self.qpcr_description}, "
            f"Controls Type: {self.controls_type}"
        )

    @staticmethod
    def _format_sheet_note(row):
        body = row[Base.NOTES]
        if body and body.strip():
            timestamp = row[Base.TIMESTAMP]
            researcher = row[Base.RESEARCHER_NAME]
            return ReportNote(body.strip(), timestamp, researcher)
        else:
            return None

    def _parse_qpcr_metadata(self, qpcr_metadata):
        row = clean_single_row(
            qpcr_metadata, QPCRMetadata.QPCR_PLATE_BARCODE, self.pcr_barcode,
        )

        self.qpcr_station = row[QPCRMetadata.QPCR_STATION]
        self.sop_protocol = row[QPCRMetadata.PROTOCOL]
        self.qpcr_description = row[QPCRMetadata.DESCRIPTION]
        self.qpcr_notes = BravoMetadata._format_sheet_note(row)


class qPCRData:
    """qPCR metadata and data"""

    data_fields = ["Well", "Fluor", "Cq"]

    PLTD_FILENAME = "Plate Setup File Name"
    PRCL_FILENAME = "Protocol File Name"

    RUN_ENDED = "Run Ended"

    def __init__(
        self,
        protocol: Protocol,
        barcode: str,
        run_info: Dict[str, str],
        quant_cq_results: pd.DataFrame,
    ):
        self.barcode = barcode
        self.metadata = run_info
        self._quant_cq_results = quant_cq_results
        logger.info(msg=f"Initializing qPCR_Metadata for Barcode: {self.barcode}")

        prcl_filename = self.metadata[qPCRData.PRCL_FILENAME]
        if prcl_filename != protocol.prcl_file:
            raise MismatchError(f"Mismatched qpcr protocol: {prcl_filename}")
        else:
            logger.info(f"Using qpcr protocol: {prcl_filename}")

        pltd_filename = self.metadata[qPCRData.PLTD_FILENAME]
        if pltd_filename != protocol.pltd_file:
            raise MismatchError(f"Mismatched plate layout: {pltd_filename}")
        else:
            logger.info(f"Using plate layout: {pltd_filename}")

    @property
    def run_ended(self):
        return self.metadata[qPCRData.RUN_ENDED]

    @property
    def data(self):
        data = defaultdict(dict)
        fields = qPCRData.data_fields
        for r in self._quant_cq_results[fields].itertuples():
            # get well and multiple fluor/cq values
            well = r.Well
            fluor = Fluor(r.Fluor)
            cq = r.Cq
            data[well][fluor] = cq
        return data
