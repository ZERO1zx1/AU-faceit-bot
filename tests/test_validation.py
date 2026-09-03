"""Tests for input validation helpers."""

from app.utils.validation import valid_among_us_name


def test_valid_name():
    assert valid_among_us_name("Zero")
    assert valid_among_us_name("Player 2")
    assert valid_among_us_name("ZERO-123")


def test_invalid_name():
    assert not valid_among_us_name("")
    assert not valid_among_us_name("a" * 33)
    assert not valid_among_us_name("Bad@Name!")
