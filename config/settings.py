"""Central application settings.

All paths, limits and logging options live here so business logic never
hardcodes them. The ``settings`` instance at the bottom is the default
configuration; tests can build their own ``Settings(...)`` with overrides.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

VALID_LOG_LEVELS: tuple[str, ...] = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


@dataclass(frozen=True)
class Settings:
    """Immutable application configuration with basic validation."""

    # Paths
    project_root: Path = PROJECT_ROOT
    raw_data_dir: Path = PROJECT_ROOT / "data" / "raw"
    processed_data_dir: Path = PROJECT_ROOT / "data" / "processed"
    sample_data_dir: Path = PROJECT_ROOT / "data" / "sample"
    reports_dir: Path = PROJECT_ROOT / "reports"
    logs_dir: Path = PROJECT_ROOT / "logs"

    # Upload rules
    max_upload_size_mb: int = 50
    allowed_extensions: tuple[str, ...] = (".csv", ".xlsx")

    # Logging
    log_level: str = "INFO"
    log_file_name: str = "app.log"
    log_max_bytes: int = 5 * 1024 * 1024
    log_backup_count: int = 3

    def __post_init__(self) -> None:
        if self.max_upload_size_mb <= 0:
            raise ValueError("max_upload_size_mb must be greater than 0")
        if not self.allowed_extensions:
            raise ValueError("allowed_extensions must not be empty")
        for ext in self.allowed_extensions:
            if not ext.startswith(".") or ext != ext.lower() or len(ext) < 2:
                raise ValueError(
                    f"Invalid extension {ext!r}: use lowercase with a leading dot, e.g. '.csv'"
                )
        if self.log_level.upper() not in VALID_LOG_LEVELS:
            raise ValueError(
                f"Invalid log_level {self.log_level!r}; choose from {VALID_LOG_LEVELS}"
            )
        if self.log_max_bytes <= 0:
            raise ValueError("log_max_bytes must be greater than 0")
        if self.log_backup_count < 0:
            raise ValueError("log_backup_count must not be negative")

    @property
    def max_upload_size_bytes(self) -> int:
        """Upload limit expressed in bytes."""
        return self.max_upload_size_mb * 1024 * 1024

    def is_extension_allowed(self, filename: str) -> bool:
        """Return True if the file name ends with an allowed extension.

        Only the final suffix is checked, case-insensitively, so
        ``report.csv.exe`` is rejected and ``DATA.CSV`` is accepted.
        """
        return Path(filename).suffix.lower() in self.allowed_extensions


settings = Settings()
