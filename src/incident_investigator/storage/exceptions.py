class LogStorageError(Exception):
    """Base error raised by log storage backends."""


class LogNotFoundError(LogStorageError):
    """Raised when a stored log object cannot be found."""


class LogIntegrityError(LogStorageError):
    """Raised when stored content does not match its checksum."""
