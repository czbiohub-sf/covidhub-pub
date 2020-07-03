import io
from typing import Any, MutableMapping, Optional

import pandas as pd

from covidhub.error import MetadataNotFoundError, MultipleRowsError
from covidhub.google.drive import DriveService, NUM_RETRIES


class CollectiveForm:
    SHEET_MIMETYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    def __init__(self, drive_service: DriveService, file_id: str, skip_header=True):
        # download the entire spreadsheet as an excel file and store in a buffer
        self.sheet_io = io.BytesIO(
            drive_service.files()
            .export(fileId=file_id, mimeType=CollectiveForm.SHEET_MIMETYPE)
            .execute(num_retries=NUM_RETRIES)
        )
        self.skip_header = skip_header

    def __getitem__(self, item):
        """Returns a dataframe from a sheet in the file from its sheet name"""
        return pd.read_excel(
            self.sheet_io, sheet_name=item, skiprows=[1] if self.skip_header else None
        )


def clean_single_row(
    df: pd.DataFrame,
    column_name: str,
    column_value: Any,
    result_index: Optional[int] = None,
) -> MutableMapping[str, Any]:
    """Given a pandas dataframe, filter the rows where a column matches a given value.
    Then use ``result_index`` to select from the remaining rows.  This resulting
    dataframe is reorganized as a mapping from column labels to value.  ``result_index``
    indicates which row from the filtered dataframe to clean.

    Parameters
    ----------
    df: pd.DataFrame
        A dataframe.
    column_name: str
        The column name to filter the rows by.
    column_value: Any
        The expected value for the column.
    result_index: Optional[int]
        The row to extract.  This obeys standard python slicing semantics (e.g., 0 =
        first row, -1 = last row).  If ``result_index`` is None and more than one row is
         in the dataframe, then MultipleMatchesError is raised.
    """
    filtered_df = df[df[column_name] == column_value]
    if len(filtered_df) == 0:
        raise MetadataNotFoundError(
            f"No metadata found for {column_name}={column_value}"
        )
    if result_index is None:
        if len(filtered_df) > 1:
            raise MultipleRowsError(
                f"Multiple matches for {column_name}={column_value}",
                match_count=len(filtered_df),
            )
        row = filtered_df.to_dict(orient="records")[-1]
    else:
        try:
            row = filtered_df.to_dict(orient="records")[result_index]
        except IndexError:
            raise MetadataNotFoundError(
                f"Requested row {result_index} from a dataset with {len(filtered_df)} "
                f"items."
            )

    return {key: None if pd.isna(value) else value for key, value in row.items()}
