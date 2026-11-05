"""The error hierarchy the whole platform raises from."""


class MeterMindError(Exception):
    """Parent of every error the platform raises deliberately."""


class UnsupportedCategoryError(MeterMindError):
    """Raised where a consumer category has no published schedule."""


class ReadingStorageError(MeterMindError):
    """Raised where a reading cannot be written or cannot be found."""


class InvalidReadingError(MeterMindError):
    """Raised where a reading cannot be true."""


class ToolError(MeterMindError):
    """Raised where an assistant tool cannot answer what it was asked."""
