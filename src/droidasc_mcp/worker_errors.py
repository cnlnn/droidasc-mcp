"""Errors shared by supervised workers and their host without host imports."""


class DroidAscError(RuntimeError):
    """Raised when Droid ASC fails or violates an adapter limit."""


def page_bounds(offset, limit, maximum):
    if offset < 0:
        raise ValueError("offset must be zero or greater")
    if limit <= 0:
        raise ValueError("limit must be greater than zero")
    return offset, min(limit, maximum)
