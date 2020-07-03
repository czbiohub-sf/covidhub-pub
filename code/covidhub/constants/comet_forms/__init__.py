from dataclasses import dataclass
from typing import Sequence


@dataclass(init=False)
class DPHSampleBatchInfoSheet:
    SHEET_NAME: str = "1-Sample_Batch_Info"
    INFO_COLUMN: str = "Sample Batch Information"
    EXTRACTION_METHOD: str = "RNA extraction kit/method:"


@dataclass(init=False)
class DPHSampleMetadata:
    SHEET_NAME: str = "2-Each_Sample_Metadata"
    EXTERNAL_ACCESSION: str = "Unique Identifier"
    COLLECTION_DATE: str = "Collection Date"
    ZIP_PREFIX: str = "First 3 digits of patient ZIP code"
    CONTAINER_NAME: str = "Sample Format"
    INITIAL_VOLUME: str = "RNA Volume (uL)"
    SPECIMEN_TYPE: str = "Original Sample Type"
    CT_1: str = "CT_1"
    CT_2: str = "CT_2"
    CT_3: str = "CT_3"
    CT_HOST: str = "CT_Host"
    DNase_TREATED: str = "DNase treated?"
    CT_DEF: str = "CT_Def"
    EXTRACTION_METHOD: str = "extraction_method"
    DATE_RECEIVED: str = "date_received"
    CZB_ID: str = "CZB_ID"
    REQUIRED_FIELDS: Sequence[str] = (
        EXTERNAL_ACCESSION,
        COLLECTION_DATE,
        ZIP_PREFIX,
        CONTAINER_NAME,
        INITIAL_VOLUME,
        SPECIMEN_TYPE,
    )
    OPTIONAL_COLUMNS: Sequence[str] = ()
    MANDATORY_COLUMNS: Sequence[str] = (
        EXTERNAL_ACCESSION,
        COLLECTION_DATE,
        CONTAINER_NAME,
        INITIAL_VOLUME,
        SPECIMEN_TYPE,
        CT_1,
        CT_2,
        CT_HOST,
        CT_DEF,
    )


@dataclass(init=False)
class CollaboratorSampleMetadata:
    CZB_ID: str = "CZB_ID"
    EXTERNAL_ACCESSION: str = "Unique Identifier"
    INITIAL_VOLUME: str = "Volume (uL)"
    NOTES: str = "Notes:"
    SPECIMEN_TYPE: str = "Original Sample Type"
    COLLECTION_DATE: str = "Collection Date"
    DATE_RECEIVED: str = "date_received"
    ZIP_PREFIX: str = "First 3 digits of patient ZIP code"
    MANDATORY_COLUMNS: Sequence[str] = (
        EXTERNAL_ACCESSION,
        INITIAL_VOLUME,
        SPECIMEN_TYPE,
        NOTES,
    )
    OPTIONAL_COLUMNS: Sequence[str] = (COLLECTION_DATE, ZIP_PREFIX)
