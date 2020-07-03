class MetadataNotFoundError(RuntimeError):
    """Raised if we expect to find metadata and don't find anything"""

    ...


class MultipleRowsError(RuntimeError):
    """Raised if we expect one entry in a dataframe and find multiple rows"""

    def __init__(self, msg, match_count=None):
        super().__init__(msg)
        self.match_count = match_count


class MismatchError(RuntimeError):
    """Raised if the metadata is inconsistent, e.g. bad file names"""

    ...


class InvalidWellID(ValueError):
    """Raised if a well ID is not a valid plate coordinate"""

    ...


class BadDriveURL(ValueError):
    """Raised is a link to a GDrive file is not formatted as we expect"""

    ...
