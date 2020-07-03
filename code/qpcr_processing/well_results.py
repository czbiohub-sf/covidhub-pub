from dataclasses import dataclass
from typing import Dict, Optional

import pandas as pd

from covidhub.constants import Call, ControlType, SIG_FIGS


@dataclass
class WellResults:
    """
    Class that holds results information for a well

    Parameters
    ----------
    call :
        the call made for the given well
    gene_cts :
        Mapping of gene name to ct value for the given well
    accession :
        the accession or control name associated with the well
    control_type :
        the type of control in the well, if it is one
    """

    accession: Optional[str] = "MISSING"
    call: Call = None
    gene_cts: Dict[str, float] = None
    control_type: Optional[ControlType] = None

    def __str__(self):
        if self.control_type is not None:
            return f"{self.control_type} {self.call}"
        else:
            return self.call.needs_review

    def format_row(self):
        return [
            self.accession,
            self.call.short,
            *(self.format_ct(gene) for gene in self.gene_cts),
        ]

    def format_ct(self, gene: str, sig_figs: int = SIG_FIGS) -> str:
        """Format a ct value for output"""
        value = self.gene_cts[gene]

        if value == "NaN" or value == "" or pd.isna(value):
            return ""
        else:
            value = int(value * 10 ** sig_figs) / 10 ** sig_figs
            return f"{value:.{sig_figs}f}"
