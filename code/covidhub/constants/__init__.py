import string
from itertools import product

from covidhub.constants.enums import (
    Call,
    ControlType,
    Fluor,
    MappedWell,
    PlateMapType,
    SamplePlateType,
)

# Set of RNA extraction protocols in the SOP. Anything else is experimental
SOP_EXTRACTIONS = {"SOP-V1", "SOP-V2", "SOP-V3"}


ROWS_96 = list(string.ascii_uppercase[:8])
COLS_96 = range(1, 13)

ROWS_384 = list(string.ascii_uppercase[:16])
COLS_384 = range(1, 25)

LAYOUT_MAP = [MappedWell.A1, MappedWell.A2, MappedWell.B1, MappedWell.B2]

# dictionary comprehension to create a 96-well to 384-well mapping. We take the
# product of ROWS_96 and COLS_96, and for each combination we map to the four wells
# in a 384 plate that are in the same location as the larger well. We put those in
# a dictionary using the LAYOUT_MAP as keys, which corresponds to the relative
# locations defined in the protocols.
#
# In the end we have a dictionary of the form (NB the inner keys are actually enums):
# {
#      ("A", 1): {"A1": ("A", 1), "A2": ("A", 2), "B1": ("B", 1), "B2": ("B", 2)},
#      ("A", 2): {"A1": ("A", 3), "A2": ("A", 4), "B1": ("B", 3), "B2": ("B", 4)},
#      ...
#      ("H", 12): {"A1": ("O", 23), "A2": ("O", 24), "B1": ("P", 23), "B2": ("P", 24)}
# }
_96_TO_384 = {
    f"{row}{col}": {
        key: (r, c)
        for key, (r, c) in zip(
            LAYOUT_MAP,
            product(ROWS_384[2 * i : 2 * i + 2], COLS_384[2 * j : 2 * j + 2]),
        )
    }
    for (i, row), (j, col) in product(enumerate(ROWS_96), enumerate(COLS_96))
}

# the quant cq file has 0-padded well numbers, but the quant amp files do not.
# So these two comprehensions take the raw mapping above and make formatted strings
MAP_96_TO_384_PADDED = {
    well_id: {k: f"{r}{c:02d}" for k, (r, c) in _96_TO_384[well_id].items()}
    for well_id in _96_TO_384
}
MAP_96_TO_384_NO_PAD = {
    well_id: {k: f"{r}{c}" for k, (r, c) in _96_TO_384[well_id].items()}
    for well_id in _96_TO_384
}


HAMILTON_COLUMN_NAMES = [
    "Deep Well Plate",
    "Deep Well Position",
    "Transfer Vol",
    "Tube Rack Carrier",
    "Tube Rack Position",
    "Tube Barcode",
    "User",
]

# column in CSV containing well
HAMILTON_WELL_COLUMN = HAMILTON_COLUMN_NAMES[1]
# column in CSV containing accession
HAMILTON_ACCESSION_COLUMN = HAMILTON_COLUMN_NAMES[5]
# accessions listed as Shield01 etc should be ignored
HAMILTON_PREFIX_FOR_EMPTY_WELLS = "Shield"

SAMPLE = "sample"

WELLLIT_NAMES_FOR_EMPTY_WELLS = [
    "CONTROL",
    "EMPTY",
    "EDIT",
]

# for plotting
MIN_Y_MAX = 1000
BACKGROUND_Y_TICKS = [100, 200, 300, 400, 500]


# the number of significant digits to print when outputting Cq values
SIG_FIGS = 2
VALID_ACCESSION = r"^[a-zA-Z]\d{4,5}$"
