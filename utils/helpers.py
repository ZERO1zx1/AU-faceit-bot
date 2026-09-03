import re

def is_valid_url(url: str) -> bool:
    regex = re.compile(r'^(?:http|ftp)s?://', re.IGNORECASE)
    return bool(regex.match(url))

def get_level_from_elo(elo: int) -> int:
    return max(1, min(10, (elo // 100) + 1))
