"""General-purpose helpers."""


from app.utils.constants import MATCH_DISPLAY_PREFIX


def generate_match_display_id(match_id: int) -> str:
    return f"{MATCH_DISPLAY_PREFIX}{match_id:08d}"


def format_elo_change(delta: int) -> str:
    return f"+{delta}" if delta > 0 else str(delta)


def get_level_from_elo(elo: int, boundaries: dict[int, int] | None = None) -> int:
    if boundaries:
        for level in sorted(boundaries.keys(), reverse=True):
            if elo >= boundaries[level]:
                return level
        return 1
    return max(1, min(10, elo // 100 + 1))
