class StreamSnapperError(Exception):
    """Base class for all StreamSnapper exceptions."""

    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        super().__init__(message)
        self.original_error = original_error


class InvalidDataError(StreamSnapperError):
    """Exception raised when invalid data is provided."""


class ScrapingError(StreamSnapperError):
    """Exception raised when an error occurs while scraping data."""


class DownloadError(StreamSnapperError):
    """Exception raised when an error occurs during download."""
