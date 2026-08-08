class ArchiveProcessingError(Exception):
    pass


class UnsupportedArchiveError(ArchiveProcessingError):
    pass


class UnsafeArchiveError(ArchiveProcessingError):
    pass


class ArchiveLimitError(ArchiveProcessingError):
    pass
