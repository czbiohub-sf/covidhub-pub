from collections import defaultdict

from covidhub.constants import MAP_96_TO_384_PADDED


def map_384_to_96(data, mapping):
    """
    Convert 384 format to 96 format. This means mapping from four wells on a 384-well to
    the original well on a 96-well plate. We use the codes A1, A2, B1, B2 to refer to
    the relative locations of the four wells.
    """
    results = defaultdict(dict)

    for well_id in MAP_96_TO_384_PADDED:
        for fluor in mapping:
            for position, gene in mapping[fluor].items():
                cq = data[MAP_96_TO_384_PADDED[well_id][position]][fluor]
                results[well_id][gene] = cq

    return results
