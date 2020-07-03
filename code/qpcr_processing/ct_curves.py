import os
from typing import Dict

import matplotlib
import matplotlib.font_manager as fm
import numpy as np
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
from pkg_resources import resource_filename

from covidhub.constants import (
    BACKGROUND_Y_TICKS,
    Call,
    COLS_96,
    Fluor,
    MAP_96_TO_384_NO_PAD,
    MIN_Y_MAX,
    ROWS_96,
)
from qpcr_processing.processing_results import ProcessingResults

pdf_resources = resource_filename("qpcr_processing", "pdf_resources")
helvetica_path = os.path.join(pdf_resources, "Helvetica.ttc")
fm.fontManager.addfont(helvetica_path)

matplotlib.rcParams.update(
    {
        "font.family": "Helvetica",
        "font.size": 8,
        "legend.handlelength": 2,
        "xtick.labelsize": 6,
        "xtick.major.size": 2,
        "ytick.labelsize": 6,
        "ytick.major.size": 2,
        "axes.titlepad": 3,
    }
)

MPL_RESULTS_COLOR_CODE = {
    Call.INV: "blue",
    Call.IND: "orange",
    Call.POS: "red",
    Call.POS_REVIEW: "red",
    Call.POS_CLUSTER: "red",
    Call.POS_HOTWELL: "red",
}


# helper function to calculate a "nice" y value to normalize against, but
# never less than MIN_Y_MAX
def nice(fluor_quant, fluor_mapping: Dict[str, str], protocol_genes):
    # select the values from fluor_quant that are part of the protocol
    wells = [
        local_map[k]
        for local_map in MAP_96_TO_384_NO_PAD.values()
        for k, g in fluor_mapping.items()
        if g in protocol_genes
    ]
    q = fluor_quant.loc[:, wells].values.max()

    # get max(p) such that 10**p < q * 1.01
    p = np.floor(np.log10(q * 1.01))

    # return min(v) over 2, 5, 10 such that v * 10**p > q
    return max(MIN_Y_MAX, min(v * 10 ** p for v in (2, 5, 10) if v * 10 ** p > q))


def add_call(ax, call: Call):
    ax.text(
        0.05,
        0.95,
        call.needs_review,
        color=MPL_RESULTS_COLOR_CODE.get(call, "black"),
        horizontalalignment="left",
        verticalalignment="top",
        transform=ax.transAxes,
    )


def _plot_96_wells(fig, y_ticks):
    """Helper function to set up a nice 8x12 gridspec and yield the axes"""
    n_rows = len(ROWS_96)
    n_cols = len(COLS_96)

    y_max = y_ticks[-1]

    gs = GridSpec(
        n_rows, n_cols, figure=fig, wspace=0.0, hspace=0.0, top=0.85, bottom=0.05
    )

    ax = None
    for i, row in enumerate(ROWS_96):
        for j, col in enumerate(COLS_96):
            ax = fig.add_subplot(gs[i, j], sharex=ax, sharey=ax)
            yield f"{row}{col}", ax

            ax.set_yticks(y_ticks)
            ax.set_yticklabels([f"{y}" if y == y_max else "" for y in y_ticks])
            ax.set_ylim(bottom=-0.05 * y_max, top=1.05 * y_max)

            if i == 0:
                ax.set_title(col)

            # turn off x ticks and labels for all but the bottom row
            if i < n_rows - 1:
                ax.tick_params(labelbottom=False, bottom=False)

            # likewise turn off y ticks for all but the leftmost column
            if j == 0:
                ax.set_ylabel(row, rotation=0, labelpad=8)
            else:
                ax.tick_params(labelleft=False, left=False)

    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=len(labels))


def plot_ct_curves(processing_results: ProcessingResults):
    """plot ct curves per well in 96 well plate"""
    well_results = processing_results.well_results
    protocol = processing_results.protocol
    quant_amp_data = processing_results.quant_amp_data

    fig = Figure(figsize=(10.5, 6))

    max_y = dict()
    gene_text = dict()

    for fluor in protocol.mapping:
        fluor_genes = set(protocol.mapping[fluor].values()).intersection(
            protocol.gene_cutoffs
        )
        max_y[fluor] = nice(quant_amp_data[fluor], protocol.mapping[fluor], fluor_genes)
        gene_text[fluor] = f"{fluor} ({', '.join(sorted(fluor_genes))})"

    max_fluors = "    ".join(
        f"{g_text} normalized to {int(round(max_y[fluor], 0))}"
        for fluor, g_text in gene_text.items()
    )

    fig.text(x=0.5, y=0.9, s=max_fluors, ha="center", fontsize=8)

    for well_id, ax in _plot_96_wells(fig, (1,)):
        for fluor in protocol.mapping:
            for idx, gene in protocol.mapping[fluor].items():
                if gene not in protocol.gene_cutoffs:
                    continue

                # Map a well_id and idx from 96-well plate to the corresponding
                # well on the 384 well plate.
                well_384 = MAP_96_TO_384_NO_PAD[well_id][idx]
                ax.plot(
                    quant_amp_data[fluor]["Cycle"],
                    np.clip(quant_amp_data[fluor][well_384] / max_y[fluor], 0, None),
                    label=gene,
                    alpha=0.8,
                )

        add_call(ax, well_results[well_id].call)

    return fig


def plot_background_ct_curves(processing_results: ProcessingResults, fluor: Fluor):
    """plot the ct curves but clamp the y axis down to look at background drift"""
    well_results = processing_results.well_results
    protocol = processing_results.protocol
    quant_amp_data = processing_results.quant_amp_data

    fig = Figure(figsize=(10.5, 6))

    for well_id, ax in _plot_96_wells(fig, BACKGROUND_Y_TICKS):
        for idx, gene in protocol.mapping[fluor].items():
            if gene not in protocol.gene_cutoffs:
                continue

            # Map a well_id and idx from 96-well plate to the corresponding
            # well on the 384 well plate.
            well_384 = MAP_96_TO_384_NO_PAD[well_id][idx]
            ax.plot(
                quant_amp_data[fluor]["Cycle"],
                quant_amp_data[fluor][well_384],
                label=gene,
                alpha=0.8,
            )

        ax.axhline(protocol.background_threshold, 0, 1, linestyle=":", color="grey")
        add_call(ax, well_results[well_id].call)

    return fig
