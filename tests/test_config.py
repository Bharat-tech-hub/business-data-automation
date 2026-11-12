"""Tests for config.settings."""

from dataclasses import FrozenInstanceError

import pytest

from config.settings import Settings, settings


def test_default_upload_limit_is_50_mb():
    assert settings.max_upload_size_mb == 50


def test_upload_limit_in_bytes():
    assert Settings(max_upload_size_mb=2).max_upload_size_bytes == 2 * 1024 * 1024


def test_default_allowed_extensions():
    assert settings.allowed_extensions == (".csv", ".xlsx")


def test_data_and_output_paths_are_inside_project_root():
    for path in (
        settings.raw_data_dir,
        settings.processed_data_dir,
        settings.sample_data_dir,
        settings.reports_dir,
        settings.logs_dir,
    ):
        assert path.is_relative_to(settings.project_root)


def test_project_root_contains_config_folder():
    assert (settings.project_root / "config").is_dir()


def test_settings_are_immutable():
    with pytest.raises(FrozenInstanceError):
        settings.max_upload_size_mb = 999  # type: ignore[misc]


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("data.csv", True),
        ("DATA.CSV", True),
        ("sales.xlsx", True),
        ("malware.exe", False),
        ("noextension", False),
        ("archive.csv.exe", False),
    ],
)
def test_extension_check(filename, expected):
    assert settings.is_extension_allowed(filename) is expected


def test_invalid_log_level_rejected():
    with pytest.raises(ValueError):
        Settings(log_level="LOUD")


@pytest.mark.parametrize("bad_limit", [0, -5])
def test_non_positive_upload_limit_rejected(bad_limit):
    with pytest.raises(ValueError):
        Settings(max_upload_size_mb=bad_limit)


@pytest.mark.parametrize("bad_ext", ["csv", ".CSV", ""])
def test_malformed_extension_rejected(bad_ext):
    with pytest.raises(ValueError):
        Settings(allowed_extensions=(bad_ext,))


def test_empty_extension_list_rejected():
    with pytest.raises(ValueError):
        Settings(allowed_extensions=())


def test_negative_log_backup_count_rejected():
    with pytest.raises(ValueError):
        Settings(log_backup_count=-1)
