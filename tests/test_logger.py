"""Tests for src.logger. Log files go to pytest temp folders, never to logs/."""

import logging
from logging.handlers import RotatingFileHandler

import pytest

from config.settings import Settings
from src.logger import ROOT_LOGGER_NAME, get_logger, setup_logging, shutdown_logging


@pytest.fixture(autouse=True)
def _cleanup_logging():
    yield
    shutdown_logging()  # closes file handles so Windows can delete temp files


def _flush(logger: logging.Logger) -> None:
    for handler in logger.handlers:
        handler.flush()


def test_setup_adds_console_and_file_handlers(tmp_path):
    logger = setup_logging(Settings(logs_dir=tmp_path))
    assert len(logger.handlers) == 2
    assert any(isinstance(h, RotatingFileHandler) for h in logger.handlers)


def test_setup_twice_does_not_duplicate_handlers(tmp_path):
    cfg = Settings(logs_dir=tmp_path)
    setup_logging(cfg)
    logger = setup_logging(cfg)
    assert len(logger.handlers) == 2


def test_message_is_written_to_log_file(tmp_path):
    cfg = Settings(logs_dir=tmp_path)
    logger = setup_logging(cfg)
    get_logger("unit_test").info("hello from test")
    _flush(logger)
    text = (tmp_path / cfg.log_file_name).read_text(encoding="utf-8")
    assert "hello from test" in text
    assert "INFO" in text
    assert f"{ROOT_LOGGER_NAME}.unit_test" in text


def test_level_filters_lower_messages(tmp_path):
    cfg = Settings(logs_dir=tmp_path, log_level="WARNING")
    logger = setup_logging(cfg)
    get_logger("unit_test").info("quiet info")
    get_logger("unit_test").warning("loud warning")
    _flush(logger)
    text = (tmp_path / cfg.log_file_name).read_text(encoding="utf-8")
    assert "quiet info" not in text
    assert "loud warning" in text


def test_level_override_argument(tmp_path):
    cfg = Settings(logs_dir=tmp_path, log_level="ERROR")
    logger = setup_logging(cfg, level="debug")
    assert logger.level == logging.DEBUG


def test_invalid_level_override_rejected(tmp_path):
    with pytest.raises(ValueError):
        setup_logging(Settings(logs_dir=tmp_path), level="LOUD")


def test_missing_log_directory_is_created(tmp_path):
    nested = tmp_path / "nested" / "logs"
    setup_logging(Settings(logs_dir=nested))
    assert nested.is_dir()


def test_shutdown_removes_handlers(tmp_path):
    logger = setup_logging(Settings(logs_dir=tmp_path))
    shutdown_logging()
    assert logger.handlers == []


def test_get_logger_is_child_of_app_logger(tmp_path):
    setup_logging(Settings(logs_dir=tmp_path))
    child = get_logger("ingestion")
    assert child.name == f"{ROOT_LOGGER_NAME}.ingestion"
    assert child.parent.name == ROOT_LOGGER_NAME
