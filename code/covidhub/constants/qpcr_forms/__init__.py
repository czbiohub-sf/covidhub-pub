from dataclasses import dataclass
from typing import Sequence

from covidhub.constants.qpcr_forms.base import Base
from covidhub.constants.qpcr_forms.reagent_prep import ReagentPrep


@dataclass(init=False)
class SampleRegistration(Base):
    SHEET_NAME = "Sample Registration"
    COURIER_NAME: str = "courier_name"
    SAMPLE_PLATE_BARCODES: Sequence[str] = (
        "sample_plate_barcode_1",
        "sample_plate_barcode_2",
        "sample_plate_barcode_3",
        "sample_plate_barcode_4",
        "sample_plate_barcode_5",
        "sample_plate_barcode_6",
        "sample_plate_barcode_7",
        "sample_plate_barcode_8",
        "sample_plate_barcode_9",
        "sample_plate_barcode_10",
    )
    PREPARED_AT: str = "prepared_at"


@dataclass(init=False)
class SampleMetadata(Base):
    SHEET_NAME = "Sample Plate Metada"
    SAMPLE_PLATE_BARCODE: str = "sample_plate_barcode"
    SAMPLE_PLATE_MAP: str = "sample_plate_map"
    SAMPLE_TYPE: str = "sample_type"
    CONTROLS_TYPE: str = "controls_type"
    SAMPLE_SOURCE: str = "sample_source"
    PLATE_LAYOUT_TYPE: str = "plate_layout_type"


@dataclass(init=False)
class FridgeCheckin(Base):
    SHEET_NAME = "4C check in"
    SAMPLE_PLATE_BARCODE: str = "sample_plate_barcode"
    SHELF: str = "shelf"
    RACK: str = "rack"
    PLATE: str = "plate"
    FRIDGE: str = "fridge"


@dataclass(init=False)
class BravoStart(Base):
    SHEET_NAME = "Starting Bravo"
    SHIFT_COORDINATOR: str = "shift_coordinator"
    SAMPLE_PLATE_BARCODE: str = "sample_plate_barcode"
    BRAVO_STATION: str = "bravo_station"
    SAMPLE_TYPE: str = "sample_type"
    EXTRACTION_VERSION: str = "extraction_version"
    DESCRIPTION: str = "starting_bravo_description"


@dataclass(init=False)
class BravoRNAExtraction(Base):
    SHEET_NAME = "Bravo RNA extractions"
    CLIAHUB_RESEARCHER: str = "cliahub_researcher"
    SAMPLE_PLATE_BARCODE: str = "sample_plate_barcode"
    RNA_PLATE_BARCODE: str = "rna_plate_barcode"
    BRAVO_STATION: str = "bravo_station"
    QPCR_PLATE_BARCODE: str = "qpcr_plate_barcode"
    SAMPLE_TYPE: str = "sample_type"
    REAGENT_PLATES: Sequence[str] = (
        "RPW1",
        "RPW2",
        "RPET12",
        "RPD1",
        "RPRPB",
        "RPET34",
        "RPH2O",
        "RPMB",
        "RPVB",
        "RPPK",
    )


@dataclass(init=False)
class RNARerun(Base):
    SHEET_NAME = "ReRun RNA Plate"
    RNA_PLATE_BARCODE: str = "rna_plate_barcode"
    BRAVO_STATION: str = "bravo_station"
    QPCR_PLATE_BARCODE: str = "qpcr_plate_barcode"


@dataclass(init=False)
class QPCRMetadata(Base):
    SHEET_NAME = "qPCR metadata"
    QPCR_PLATE_BARCODE: str = "qpcr_plate_barcode"
    QPCR_STATION: str = "qpcr_station"
    PROTOCOL: str = "protocol"
    DESCRIPTION: str = "description"


@dataclass(init=False)
class SampleRerun(Base):
    SHEET_NAME = "Sample Rerun"
    SAMPLE_ACCESSION: str = "sample_accession"
    ORIGINAL_SAMPLE_PLATE_BARCODE: str = "original_sample_plate_barcode"
    ORIGINAL_WELL: str = "original_well"
    NEW_SAMPLE_PLATE_BARCODE: str = "new_sample_plate_barcode"
    NEW_WELL: str = "new_well"
    RESEARCHER_NAME: str = "shift_supervisor"  # overriding this value


@dataclass(init=False)
class FreezerCheckin(Base):
    SHEET_NAME = "minus80 Checkin"
    SAMPLE_PLATE_BARCODE: str = "sample_plate_barcode"
    RNA_PLATE_BARCODE: str = "rna_plate_barcode"
    FREEZER: str = "freezer"
    SHELF: str = "shelf"
    RACK: str = "rack"
    BLOCK_A: str = "block_a"
    BLOCK_B: str = "block_b"
    RNA_FREEZER: str = "rna_freezer"
    RNA_SHELF: str = "rna_shelf"
    RNA_RACK: str = "rna_rack"
    RNA_BLOCK_A: str = "rna_block_a"
    RNA_BLOCK_B: str = "rna_block_b"
    SAMPLE_TYPE: str = "sample_type"
    RNA_RECHECKIN_BARCODES: Sequence[str] = (
        "plate_barcode_1",
        "plate_barcode_2",
        "plate_barcode_3",
        "plate_barcode_4",
        "plate_barcode_5",
        "plate_barcode_6",
        "plate_barcode_7",
        "plate_barcode_8",
        "plate_barcode_9",
        "plate_barcode_10",
    )


@dataclass(init=False)
class FreezerCheckout(Base):
    SHEET_NAME = "minus80 Checkout"
    SAMPLE_PLATE_BARCODE: str = "sample_plate_barcode"
    RNA_PLATE_BARCODE: str = "rna_plate_barcode"
    FREEZER: str = "freezer"
    NOTES: str = "notes"


@dataclass(init=False)
class WasteManagement(Base):
    SHEET_NAME = "Waste Discard"
    DRUMS: Sequence[str] = (
        "waste_drum_barcode_1",
        "waste_drum_barcode_2",
        "waste_drum_barcode_3",
        "waste_drum_barcode_4",
        "waste_drum_barcode_5",
        "waste_drum_barcode_6",
        "waste_drum_barcode_7",
        "waste_drum_barcode_8",
        "waste_drum_barcode_9",
        "waste_drum_barcode_10",
    )
    DRUMS_NOTES: str = "waste_drum_notes"
    BOTTLES: Sequence[str] = (
        "waste_bottle_barcode_1",
        "waste_bottle_barcode_2",
        "waste_bottle_barcode_3",
        "waste_bottle_barcode_4",
        "waste_bottle_barcode_5",
        "waste_bottle_barcode_6",
        "waste_bottle_barcode_7",
        "waste_bottle_barcode_8",
        "waste_bottle_barcode_9",
        "waste_bottle_barcode_10",
    )
    BOTTLES_NOTES: str = "waste_bottle_notes"
    PLATES: Sequence[str] = (
        "waste_plate_barcode_1",
        "waste_plate_barcode_2",
        "waste_plate_barcode_3",
        "waste_plate_barcode_4",
        "waste_plate_barcode_5",
    )
    PLATES_NOTES: str = "waste_plate_notes"
