"""Centralized, file-backed logging configuration for the bot."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import settings

LOG_FILE = Path("logs/cogs.txt")


def setup_logging(log_file: str | Path = LOG_FILE) -> Path:
    """Configure console and rotating UTF-8 file logging.

    Calling this function more than once is safe: handlers installed by an
    earlier call are replaced instead of duplicated.
    """
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)

    for handler in list(root.handlers):
        if getattr(handler, "_au_faceit_handler", False):
            root.removeHandler(handler)
            handler.close()

    fmt = logging.Formatter(
        "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)s | "
        "%(filename)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    console._au_faceit_handler = True  # type: ignore[attr-defined]  # reason: dynamic tag so test_logging.py can find stdout/stderr handlers
    root.addHandler(console)

    path = Path(log_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        path,
        maxBytes=10_000_000,
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    file_handler._au_faceit_handler = True  # type: ignore[attr-defined]  # reason: dynamic tag so test_logging.py can find stdout/stderr handlers
    root.addHandler(file_handler)
    logging.captureWarnings(True)
    return path


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
