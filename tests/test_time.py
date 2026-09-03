"""Tests for time formatting helpers."""

from app.utils.time import format_duration


def test_format_duration():
    assert format_duration(0) == "0m 00s"
    assert format_duration(195681) == "54h 21m"
