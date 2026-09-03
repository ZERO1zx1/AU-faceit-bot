"""Tests for helper utilities."""

from app.utils.helpers import format_elo_change, get_level_from_elo


def test_format_elo_change():
    assert format_elo_change(8) == "+8"
    assert format_elo_change(-6) == "-6"
    assert format_elo_change(0) == "0"


def test_level_default():
    assert get_level_from_elo(500) == 6
    assert get_level_from_elo(2000) == 10
    assert get_level_from_elo(150) == 2


def test_level_custom_boundaries():
    boundaries = {1: 0, 5: 1000, 10: 1700}
    assert get_level_from_elo(700, boundaries) == 1
    assert get_level_from_elo(1200, boundaries) == 5
    assert get_level_from_elo(1800, boundaries) == 10
