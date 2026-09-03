"""Time formatting helpers."""

from datetime import UTC, datetime, timedelta, timezone

_AWST = timezone(timedelta(hours=8))  # adjust as needed


def utc_now() -> datetime:
    return datetime.now(UTC)


def format_duration(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m {seconds % 60:02d}s"


def discord_timestamp(dt: datetime) -> str:
    ts = int(dt.timestamp())
    return f"<t:{ts}:R>"
