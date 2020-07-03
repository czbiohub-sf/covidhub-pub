from dataclasses import dataclass
from typing import Sequence

from covidhub.constants.qpcr_forms.base import Cols


@dataclass(init=False)
class RNA(Cols):
    ...


@dataclass(init=False)
class RPPK(Cols):
    PROTEINASE_K: str = "rppk_proteinase_k"
    PROTEINASE_K_BUFFER: str = "rppk_proteinase_k_buffer"


@dataclass(init=False)
class RPVB(Cols):
    VIRAL_BUFFER: str = "rpvb_viral_buffer"
    BME: str = "rpvb_bme"


@dataclass(init=False)
class RPPB(Cols):
    """DEPRECATED, only included for older plates"""

    PATHOGEN_BUFFER: str = "rpvb_viral_buffer"
    BME: str = "rpvb_bme"


@dataclass(init=False)
class RPMB(Cols):
    MAGBEADS: str = "rpmb_magbeads"


@dataclass(init=False)
class RPW1(Cols):
    WASH_BUFFER_1: str = "rpw1_wash_buffer_1"
    ISOPROPANOL: str = "rpw1_isopropanol"


@dataclass(init=False)
class RPW2(Cols):
    WASH_BUFFER_2: str = "rpw2_wash_buffer_2"
    ISOPROPANOL: str = "rpw2_isopropanol"


@dataclass(init=False)
class RPET(Cols):
    ETHANOL: str = "rpet_ethanol"


@dataclass(init=False)
class RPD1(Cols):
    DNASEI: str = "rpd1_dnaseI"
    DIGESTION_BUFFER: str = "rpd1_digestion_buffer"
    WATER: str = "rpd1_water"


@dataclass(init=False)
class RPRPB(Cols):
    RNA_PREP_BUFFER: str = "rprpb_rna_prep_buffer"


@dataclass(init=False)
class RPH2O(Cols):
    WATER: str = "rph2o_water"


@dataclass(init=False)
class SP(Cols):
    DNA_RNA_SHIELD: str = "sp_dna-rna_shield"


@dataclass(init=False)
class V1(Cols):
    NAME = "SOP-V1"
    TAQPATH: str = "qpcr_v1_taqpath"
    RDRP_FWD: str = "qpcr_v1_rdrp_fwd"
    RDRP_REV: str = "qpcr_v1_rdrp_rev"
    RDRP_FAM: str = "qpcr_v1_rdrp_fam"
    RNAP_FWD: str = "qpcr_v1_rnap_fwd"
    RNAP_REV: str = "qpcr_v1_rnap_rev"
    RNAP_FAM: str = "qpcr_v1_rnap_fam"
    EGENE_FWD: str = "qpcr_v1_e-gene_fwd"
    EGENE_REV: str = "qpcr_v1_e-gene_rev"
    EGENE_FAM: str = "qpcr_v1_e-gene_fam"
    WATER: str = "qpcr_v1_water"
    NOTES: str = "qpcr_v1_notes"


@dataclass(init=False)
class V2(Cols):
    NAME = "SOP-V2"
    LUNA_MM: str = "qpcr_v2_luna_mm"
    RNAP_FWD: str = "qpcr_v2_rnap_fwd"
    RNAP_REV: str = "qpcr_v2_rnap_rev"
    RNAP_HEX: str = "qpcr_v2_rnap_hex"
    EGENE_FWD: str = "qpcr_v2_e-gene_fwd"
    EGENE_REV: str = "qpcr_v2_e-gene_rev"
    EGENE_FAM: str = "qpcr_v2_e-gene_fam"
    NGENE_FWD: str = "qpcr_v2_n-gene_fwd"
    NGENE_REV: str = "qpcr_v2_n-gene_rev"
    NGENE_FAM: str = "qpcr_v2_n-gene_fam"
    WATER: str = "qpcr_v2_water"
    NOTES: str = "qpcr_v2_notes"


@dataclass(init=False)
class UDG(Cols):
    NAME = "UDGprotocol"
    LUNA_MM: str = "qpcr_udgprotocol_luna_mm"
    RNAP_FWD: str = "qpcr_udgprotocol_rnap_fwd"
    RNAP_REV: str = "qpcr_udgprotocol_rnap_rev"
    RNAP_HEX: str = "qpcr_udgprotocol_rnap_hex"
    EGENE_FWD: str = "qpcr_udgprotocol_e-gene_fwd"
    EGENE_REV: str = "qpcr_udgprotocol_e-gene_rev"
    EGENE_FAM: str = "qpcr_udgprotocol_e-gene_fam"
    EGENE_CY5: str = "qpcr_udgprotocol_e-gene_cy5"
    NGENE_FWD: str = "qpcr_udgprotocol_n-gene_fwd"
    NGENE_REV: str = "qpcr_udgprotocol_n-gene_rev"
    NGENE_FAM: str = "qpcr_udgprotocol_n-gene_fam"
    WATER: str = "qpcr_udgprotocol_water"
    NOTES: str = "qpcr_udgprotocol_notes"


@dataclass(init=False)
class V3(Cols):
    NAME = "SOP-V3"
    LUNA_MM: str = "qpcr_v3_luna_mm"
    RNAP_FWD: str = "qpcr_v3_rnap_fwd"
    RNAP_REV: str = "qpcr_v3_rnap_rev"
    RNAP_HEX: str = "qpcr_v3_rnap_hex"
    EGENE_FWD: str = "qpcr_v3_e-gene_fwd"
    EGENE_REV: str = "qpcr_v3_e-gene_rev"
    EGENE_FAM: str = "qpcr_v3_e-gene_fam"
    NGENE_FWD: str = "qpcr_v3_n-gene_fwd"
    NGENE_REV: str = "qpcr_v3_n-gene_rev"
    NGENE_FAM: str = "qpcr_v3_n-gene_fam"
    WATER: str = "qpcr_v3_water"
    NOTES: str = "qpcr_v3_notes"


QPCR = {"v1": V1, "v2": V2, "v2-40": V2, "UDGprotocol": UDG, "v3": V3}


@dataclass(init=False)
class ReagentPrep(Cols):
    SHEET_NAME = "Reagent Tracking"
    TIMESTAMP: str = "timestamp"
    RESEARCHER_NAME: str = "researcher_name"
    REAGENT_PLATE_BARCODES: Sequence[str] = (
        "reagent_plate_barcode_1",
        "reagent_plate_barcode_2",
        "reagent_plate_barcode_3",
        "reagent_plate_barcode_4",
        "reagent_plate_barcode_5",
        "reagent_plate_barcode_6",
        "reagent_plate_barcode_7",
        "reagent_plate_barcode_8",
        "reagent_plate_barcode_9",
        "reagent_plate_barcode_10",
    )
    PLATE_TYPE: str = "plate_type"
    QPCR_TYPE: str = "qpcr_type"

    PLATE_TYPES = {
        "Proteinase K": RPPK,
        "MagBinding Beads": RPMB,
        "DNase I": RPD1,
        "Water": RPH2O,
        "qPCR plate": QPCR,
        "RNA plate": RNA,
        "RNA Prep Buffer": RPRPB,
        "Viral DNA/RNA Buffer": RPVB,
        "Pathogen DNA/RNA Buffer": RPPB,
        "Sample Plate": SP,
        "Ethanol 1+2": RPET,
        "Ethanol 3+4": RPET,
        "Ethanol 1+2+3+4": RPET,
        "Wash Buffer 1": RPW1,
        "Wash Buffer 2": RPW2,
    }
