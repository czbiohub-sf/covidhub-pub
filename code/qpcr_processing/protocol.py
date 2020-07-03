import math
from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Union

import numpy as np

from covidhub.constants import Call, ControlType, Fluor, MappedWell, SAMPLE
from qpcr_processing.well_results import WellResults

Gene = str
CqVal = Optional[float]

WellMapping = Dict[Fluor, Dict[MappedWell, Gene]]
GeneThresholds = Dict[Union[str, ControlType], CqVal]


# helper function to act as a constructor for GeneThresholds
def cq_thresholds(
    sample: CqVal, pc: CqVal, ntc: CqVal, hrc: CqVal, pbs: CqVal
) -> GeneThresholds:
    return {
        SAMPLE: sample,
        ControlType.PC: pc,
        ControlType.NTC: ntc,
        ControlType.HRC: hrc,
        ControlType.PBS: pbs,
    }


def get_protocol(protocol_name):
    if protocol_name == SOP_V1.name:
        return SOP_V1
    elif protocol_name == SOP_V2.name:
        return SOP_V2
    elif protocol_name == UDGprotocol.name:
        return UDGprotocol
    elif protocol_name == SOP_V3.name:
        return SOP_V3
    else:
        raise ValueError(f"Unknown protocol {protocol_name}")


@dataclass
class Protocol:
    """Dataclass for protocols. They should have all of these fields. Subclasses can
    overwrite to change the logic
    """

    name: str
    experimental: bool
    prcl_file: str
    pltd_file: str
    virus_genes: Dict[Gene, GeneThresholds]
    control_genes: Dict[Gene, GeneThresholds]
    mapping: WellMapping
    background_threshold: int = 200
    radius: int = 1
    pos_cluster_cutoff: float = 10.0

    @staticmethod
    def isnan(v):
        return v == "NaN" or v == "" or math.isnan(v)

    @property
    def gene_cutoffs(self):
        return {
            gene: gene_cutoffs
            for gene_dict in (self.virus_genes, self.control_genes)
            for gene, gene_cutoffs in gene_dict.items()
        }

    @property
    def gene_list(self):
        return list(self.gene_cutoffs)

    @property
    def formatted_row_header(self):
        header = ["Well", "Accession", "Call"]
        header.extend(f"{gene} Ct" for gene in self.gene_list)

        return header

    def format_header_for_reports(self, start) -> Sequence[str]:
        formatted = [f"{gene} Ct" for gene in self.gene_list]
        return [start + formatted]

    def call_ct_value(
        self, g: str, v: float, well_type: Union[str, ControlType]
    ) -> bool:
        if self.isnan(v):
            # not detected at all
            return False
        elif g not in self.gene_cutoffs:
            # this gene is not part of the protocol
            return False
        elif self.gene_cutoffs[g][well_type] is None:
            # if cutoff is None, any value passes cutoff
            return True
        elif float(v) >= self.gene_cutoffs[g][well_type]:
            # if cutoff is not None, check if value is above cutoff
            return False
        elif float(v) < self.gene_cutoffs[g][well_type]:
            # check if value is below cutoff, just in case
            return True
        else:
            # who knows how this could happen
            raise ValueError(f"Illegal Ct value {v}")

    def call_well(self, values) -> Call:
        detected_genes = {g for g, v in values.items() if not self.isnan(v)}
        called_genes = {
            g for g, v in values.items() if self.call_ct_value(g, v, SAMPLE)
        }

        if detected_genes.intersection(self.virus_genes):
            # viral genes were detected
            if called_genes.issuperset(self.virus_genes):
                # if all viral genes were below cutoff, sample is positive
                return Call.POS
            else:
                # if something else happened, the sample is indeterminate
                return Call.IND
        else:
            # no viral genes were detected at all
            if called_genes == set(self.control_genes):
                # if the control genes are below cutoff, the sample is negative
                return Call.NEG
            else:
                # otherwise the sample is invalid
                return Call.INV

    def check_control(self, values, control_type) -> Call:
        called_genes = {
            g for g, v in values.items() if self.call_ct_value(g, v, control_type)
        }
        status = Call.FAIL

        if control_type in {ControlType.NTC, ControlType.PBS}:
            # no genes should be detected at all
            if len(called_genes) == 0:
                status = Call.PASS
        elif control_type == ControlType.PC:
            # all genes should all be detected below threshold
            if called_genes == set(self.gene_cutoffs):
                status = Call.PASS
        elif control_type == ControlType.HRC:
            # only control genes detected, no viral genes at all
            if called_genes == set(self.control_genes):
                status = Call.PASS
        else:
            raise ValueError(f"Unrecognized control type: {control_type}.")

        return status

    def get_failure_details(self, control_type):
        if control_type in {ControlType.NTC, ControlType.PBS}:
            # water/PBS fails if not all genes are ND
            detailed_status = ", ".join(f"Need {gene} = ND" for gene in self.gene_list)
        elif control_type == ControlType.PC:
            # pc fails if virus genes above cutoff
            detailed_status = ", ".join(
                f"Need {gene} < {self.virus_genes[gene][control_type]}"
                for gene in self.virus_genes
            )
        elif control_type == ControlType.HRC:
            # hrc fails if virus genes detected and control genes above cutoff
            virus_failure = ", ".join(f"Need {gene} = ND" for gene in self.virus_genes)
            control_failure = ", ".join(
                f"{gene} < {self.control_genes[gene][control_type]}"
                for gene in self.control_genes
            )

            detailed_status = f"{virus_failure} and {control_failure}"
        else:
            raise ValueError(f"Unrecognized control type: {control_type}")

        return detailed_status

    def compare_wells(
        self, results: WellResults, other_results: WellResults, cutoff: float
    ):
        """
        Compares two positive wells and decides whether the first might be contamination
        from the second. This version compares the mean of all viral genes. If any gene
        is NaN, it will return False.
        """
        well_mean = np.mean([results.gene_cts[g] for g in self.virus_genes])
        other_mean = np.mean([other_results.gene_cts[g] for g in self.virus_genes])

        return well_mean - other_mean > cutoff

    def check_square(
        self,
        well_mapping: Dict[str, WellResults],
        radius: int,
        cutoff: float,
        flag: Call,
    ):
        """
        Takes a list of wells with ct values and calls. For each positive well, check if
        there is another well within an NxN square that has a lower Cq, such that the
        difference is above a cutoff.

        Parameters
        ----------
        well_mapping :
            A dictionary mapping from wells to WellResults instances
        radius :
            The "radius" of the square to consider: NxN where N = 2r+1
        cutoff :
            Cutoff to check when flagging a possible contamination
        flag :
            The Call type to set any flagged result
        Returns
        -------
        list
            Returns a list of the wells that should be rerun due to possible overflow
        """

        for well_id, results in well_mapping.items():
            if not results.call.is_positive:
                continue

            row = ord(well_id[:1])
            col = int(well_id[1:])

            # Get the adjacent wells. This will look at wells within +- a given
            # distance including the current well. Since the current well has no
            # difference with itself it won't cause any issues to include it.
            for other_row in map(chr, range(row - radius, row + radius + 1)):
                for other_col in range(col - radius, col + radius + 1):
                    other_well = f"{other_row}{other_col}"
                    if other_well not in well_mapping:
                        continue

                    other_results = well_mapping.get(other_well)
                    if not results.call.is_positive:
                        continue

                    if self.compare_wells(results, other_results, cutoff):
                        results.call = flag

    def flag_contamination(self, well_mapping: Dict[str, WellResults]):
        self.check_square(
            well_mapping, self.radius, self.pos_cluster_cutoff, Call.POS_CLUSTER
        )


SOP_V1 = Protocol(
    name="SOP-V1",
    experimental=False,
    prcl_file="Covid19_protocol.prcl",
    pltd_file="Covid19_platelayout.pltd",
    radius=0,
    virus_genes={
        "RdRp": cq_thresholds(40.0, 40.0, None, None, None),
        "E": cq_thresholds(40.0, 40.0, None, None, None),
    },
    control_genes={"RNAse P": cq_thresholds(40.0, 40.0, None, 40.0, None)},
    mapping={
        Fluor.FAM: {MappedWell.A1: "RdRp", MappedWell.A2: "E", MappedWell.B1: "RNAse P"}
    },
)


SOP_V2 = Protocol(
    name="SOP-V2",
    experimental=False,
    prcl_file="Covid19-LUNA_protocol.prcl",
    pltd_file="Covid19-v2_platelayout.pltd",
    virus_genes={
        "N": cq_thresholds(40.0, 38.0, None, None, None),
        "E": cq_thresholds(40.0, 38.0, None, None, None),
    },
    control_genes={"RNAse P": cq_thresholds(36.0, 38.0, None, 36.0, None)},
    mapping={
        Fluor.FAM: {MappedWell.A1: "N", MappedWell.A2: "E"},
        Fluor.HEX: {MappedWell.B1: "RNAse P"},
    },
)


UDGprotocol = Protocol(
    name="UDGprotocol",
    experimental=True,
    prcl_file="Covid19-UDG.prcl",
    pltd_file="Covid19-v2_platelayout.pltd",
    background_threshold=300,
    virus_genes={
        "N": cq_thresholds(40.0, 38.0, None, None, None),
        "E": cq_thresholds(40.0, 38.0, None, None, None),
    },
    control_genes={"RNAse P": cq_thresholds(36.0, 38.0, None, 36.0, None)},
    mapping={
        Fluor.FAM: {MappedWell.A1: "N", MappedWell.A2: "E"},
        Fluor.HEX: {MappedWell.B1: "RNAse P"},
    },
)


@dataclass
class V3Protocol(Protocol):
    hot_well_radius: int = 3
    hot_well_cutoff: int = 22.0

    def call_well(self, values):
        super_call = super().call_well(values)
        if super_call == Call.IND:
            # instead of indeterminate, the sample is "suspiciously positive"
            return Call.POS_REVIEW
        else:
            return super_call

    def compare_wells(
        self, results: WellResults, other_results: WellResults, cutoff: float
    ):
        """
        Compares two positive wells and decides whether the first might be contamination
        from the second. This version compares each gene separately and uses OR logic to
        combine the results
        """
        for g in self.virus_genes:
            if results.gene_cts[g] - other_results.gene_cts[g] > cutoff:
                return True
        else:
            return False

    def flag_contamination(self, well_mapping: Dict[str, WellResults]):
        # first, check for "hot wells" that contaminate distant positives
        self.check_square(
            well_mapping, self.hot_well_radius, self.hot_well_cutoff, Call.POS_HOTWELL
        )
        # then, check the neighbor wells. Given both possibilities, this is more likely
        self.check_square(
            well_mapping, self.radius, self.pos_cluster_cutoff, Call.POS_CLUSTER
        )


SOP_V3 = V3Protocol(
    name="SOP-V3",
    experimental=False,
    prcl_file="Covid19-LUNA_protocol.prcl",
    pltd_file="Covid19-v2_platelayout.pltd",
    background_threshold=300,
    pos_cluster_cutoff=15.0,
    virus_genes={
        "N": cq_thresholds(40.0, 38.0, None, None, None),
        "E": cq_thresholds(40.0, 38.0, None, None, None),
    },
    control_genes={"RNAse P": cq_thresholds(None, 38.0, None, 36.0, None)},
    mapping={
        Fluor.FAM: {MappedWell.A1: "N", MappedWell.A2: "E"},
        Fluor.HEX: {MappedWell.B1: "RNAse P"},
    },
)
