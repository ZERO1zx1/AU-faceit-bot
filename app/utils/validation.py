"""Input validation helpers."""

import re

_NAME_MAX_LEN = 32
_INVALID_NAME_CHARS = re.compile(r"[^\w\s-]", re.UNICODE)


def valid_among_us_name(name: str) -> bool:
    if not name or len(name) > _NAME_MAX_LEN:
        return False
    return _INVALID_NAME_CHARS.search(name) is None
