"""Shared archive diagnostics across supervised entry points."""


class ArchiveError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
