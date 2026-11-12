"""Structured logging setup for the application.

Use ``setup_logging()`` once at program start (for example in ``run.py`` or the
Streamlit entry point), then ``get_logger(__name__)`` in each module.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from config.settings import VALID_LOG_LEVELS, Settings, settings as default_settings

ROOT_LOGGER_NAME = "business_analytics"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _resolve_level(level_name: str) -> int:
    """Convert a level name such as 'info' to its numeric logging value."""
    name = level_name.upper()
    if name not in VALID_LOG_LEVELS:
        raise ValueError(f"Invalid log level {level_name!r}; choose from {VALID_LOG_LEVELS}")
    return getattr(logging, name)


def shutdown_logging() -> None:
    """Close and remove every handler owned by the application logger."""
    logger = logging.getLogger(ROOT_LOGGER_NAME)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


def setup_logging(config: Settings | None = None, level: str | None = None) -> logging.Logger:
    """Configure console and rotating-file logging; safe to call repeatedly.

    Args:
        config: Settings to use. Defaults to the global ``settings``.
        level: Optional level name that overrides ``config.log_level``.

    Returns:
        The configured application logger.

    Raises:
        ValueError: If the level name is not valid.
    """
    cfg = config or default_settings
    level_value = _resolve_level(level or cfg.log_level)

    shutdown_logging()  # prevents duplicate handlers on repeated calls

    logger = logging.getLogger(ROOT_LOGGER_NAME)
    logger.setLevel(level_value)
    logger.propagate = False

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    cfg.logs_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        cfg.logs_dir / cfg.log_file_name,
        maxBytes=cfg.log_max_bytes,
        backupCount=cfg.log_backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger such as ``business_analytics.ingestion``."""
    return logging.getLogger(f"{ROOT_LOGGER_NAME}.{name}")
