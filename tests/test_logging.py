"""Tests for the persistent error log."""

import logging
from pathlib import Path

from app.logging import get_logger, setup_logging


def _flush_handlers() -> None:
    for handler in logging.getLogger().handlers:
        handler.flush()


def test_exception_is_written_with_full_traceback(tmp_path: Path) -> None:
    log_file = setup_logging(tmp_path / "logs" / "cogs.txt")
    logger = get_logger("tests.error")

    try:
        raise ZeroDivisionError("test traceback")
    except ZeroDivisionError:
        logger.exception("Test command failed | guild_id=123 user_id=456")

    _flush_handlers()
    contents = log_file.read_text(encoding="utf-8")
    assert "Test command failed | guild_id=123 user_id=456" in contents
    assert "ZeroDivisionError" in contents
    assert "Traceback (most recent call last)" in contents


def test_setup_logging_does_not_duplicate_file_handlers(tmp_path: Path) -> None:
    log_file = tmp_path / "logs" / "cogs.txt"
    setup_logging(log_file)
    setup_logging(log_file)

    get_logger("tests.once").error("ONE_UNIQUE_ERROR")
    _flush_handlers()

    assert log_file.read_text(encoding="utf-8").count("ONE_UNIQUE_ERROR") == 1
