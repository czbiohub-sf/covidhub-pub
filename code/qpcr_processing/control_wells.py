import logging
import re
from typing import Dict, Optional

from covidhub.constants import VALID_ACCESSION
from covidhub.constants.controls import (
    CONTROL_NAMES,
    STANDARD_CONTROL_WELLS,
    VALIDATION_CONTROL_WELLS,
)
from covidhub.constants.enums import ControlsMappingType

logger = logging.getLogger(__name__)


def get_control_wells_from_type(
    controls_type: ControlsMappingType, accession_data: Optional[Dict] = None
):
    """Return the control wells for the sample plate based off the controls_type filled out in
    the Sample Plate Registration form"""
    if controls_type == ControlsMappingType.Standard:
        logger.info(msg="Using standard control wells")
        return STANDARD_CONTROL_WELLS
    if controls_type == ControlsMappingType.Validation:
        logger.info(msg="Using standard validation control wells")
        return VALIDATION_CONTROL_WELLS
    if controls_type == ControlsMappingType.NoControls:
        logger.info(msg="ControlsType.NoControls, returning empty mapping")
        return {}
    if controls_type == ControlsMappingType.Custom:
        logger.info(msg="Custom controls, getting from accession data")
        # get just controls from plate map data
        return {
            key: CONTROL_NAMES[val]
            for key, val in accession_data.items()
            if val in CONTROL_NAMES
        }


def update_accession_data_with_controls(
    control_wells: Dict, accession_data: Dict, barcode: str
):
    """Check that the control wells don't overwrite any valid accessions before inserting them"""
    for well in control_wells.keys():
        if well in accession_data:
            if re.match(VALID_ACCESSION, accession_data[well].rstrip()):
                raise ValueError(
                    f"The control mapping for {barcode} overwrites a valid accession, "
                    f"aborting run"
                )
    accession_data.update(control_wells)
