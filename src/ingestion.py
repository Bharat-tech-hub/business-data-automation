"""Safe ingestion of CSV and XLSX sales files.

Loads raw data and reports what happened. Type and date parsing is deliberately
left to the validation step so that bad values are counted, not fatal.
"""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from config.settings import Settings, settings as default_settings
from src.logger import get_logger
from src.schema import REQUIRED_COLUMNS

logger = get_logger("ingestion")

MAX_UNCOMPRESSED_FACTOR = 20  # zip-bomb guard: uncompressed size vs. size limit


class IngestionError(Exception):
    """Base class for blocking ingestion problems."""


class UnsupportedFileTypeError(IngestionError):
    """The file extension is not allowed."""


class EmptyFileError(IngestionError):
    """The file has no content or no data rows."""


class FileTooLargeError(IngestionError):
    """The file exceeds the configured size limit."""


class CorruptFileError(IngestionError):
    """The content does not match the declared file type or cannot be read."""


class MissingColumnsError(IngestionError):
    """One or more required columns are absent."""


@dataclass
class IngestionResult:
    """Facts about a completed load."""

    file_name: str
    file_format: str
    size_bytes: int
    rows: int
    columns: int
    encoding: str | None = None
    warnings: list[str] = field(default_factory=list)


def sanitize_filename(name: str) -> str:
    """Return a safe base name: no directories, only letters, digits, . _ - and spaces."""
    base = re.split(r"[\\/]", name or "")[-1].strip()
    base = re.sub(r"[^A-Za-z0-9._ -]", "_", base)
    base = base.lstrip(".")
    return base or "upload"


def _check_xlsx(data: bytes, cfg: Settings) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()
            if "xl/workbook.xml" not in names:
                raise CorruptFileError("The file is not a valid Excel workbook (no workbook.xml).")
            total = sum(info.file_size for info in zf.infolist())
            if total > cfg.max_upload_size_bytes * MAX_UNCOMPRESSED_FACTOR:
                raise CorruptFileError("The workbook expands to an unsafe size and was rejected.")
    except zipfile.BadZipFile as exc:
        raise CorruptFileError("The file is not a valid .xlsx (not a zip archive).") from exc


def _read_csv(data: bytes) -> tuple[pd.DataFrame, str]:
    if b"\x00" in data:
        raise CorruptFileError("The file contains binary data and is not a valid CSV.")
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        try:
            df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=True)
        except pd.errors.EmptyDataError as exc:
            raise EmptyFileError("The CSV file has no content.") from exc
        except pd.errors.ParserError as exc:
            raise CorruptFileError(f"The CSV could not be parsed: {exc}") from exc
        return df, encoding
    raise CorruptFileError("The CSV could not be decoded.")


def _read_xlsx(data: bytes, warnings: list[str]) -> pd.DataFrame:
    try:
        sheets = pd.ExcelFile(io.BytesIO(data), engine="openpyxl")
    except Exception as exc:  # openpyxl raises several exception types
        raise CorruptFileError(f"The Excel file could not be read: {exc}") from exc
    if not sheets.sheet_names:
        raise EmptyFileError("The workbook has no sheets.")
    if len(sheets.sheet_names) > 1:
        warnings.append(
            f"Workbook has {len(sheets.sheet_names)} sheets; only the first "
            f"('{sheets.sheet_names[0]}') was read."
        )
    return pd.read_excel(io.BytesIO(data), sheet_name=sheets.sheet_names[0], engine="openpyxl")


def load_bytes(
    data: bytes, file_name: str, config: Settings | None = None
) -> tuple[pd.DataFrame, IngestionResult]:
    """Validate and load uploaded bytes. Raises an ``IngestionError`` subclass on failure."""
    cfg = config or default_settings
    safe_name = sanitize_filename(file_name)
    suffix = Path(safe_name).suffix.lower()
    warnings: list[str] = []

    if not cfg.is_extension_allowed(safe_name):
        allowed = ", ".join(cfg.allowed_extensions)
        raise UnsupportedFileTypeError(f"'{safe_name}' is not supported. Allowed types: {allowed}.")
    if not data:
        raise EmptyFileError(f"'{safe_name}' is empty.")
    if len(data) > cfg.max_upload_size_bytes:
        raise FileTooLargeError(
            f"'{safe_name}' is {len(data) / 1024 / 1024:.1f} MB; the limit is "
            f"{cfg.max_upload_size_mb} MB."
        )

    encoding: str | None = None
    if suffix == ".xlsx":
        _check_xlsx(data, cfg)
        df = _read_xlsx(data, warnings)
        file_format = "xlsx"
    else:
        df, encoding = _read_csv(data)
        file_format = "csv"
        if encoding == "latin-1":
            warnings.append("File is not valid UTF-8; it was decoded as Latin-1.")

    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise MissingColumnsError(f"Missing required column(s): {', '.join(missing)}.")
    extra = [c for c in df.columns if c not in REQUIRED_COLUMNS]
    if extra:
        warnings.append(f"Unexpected extra column(s) kept as-is: {', '.join(extra)}.")
    if df.empty:
        raise EmptyFileError(f"'{safe_name}' has a header but no data rows.")

    result = IngestionResult(
        file_name=safe_name,
        file_format=file_format,
        size_bytes=len(data),
        rows=len(df),
        columns=len(df.columns),
        encoding=encoding,
        warnings=warnings,
    )
    logger.info("Loaded %s: %d rows x %d columns", safe_name, result.rows, result.columns)
    for message in warnings:
        logger.warning("%s: %s", safe_name, message)
    return df, result


def load_file(
    path: str | Path, config: Settings | None = None
) -> tuple[pd.DataFrame, IngestionResult]:
    """Load a file from disk. The file is only read, never modified."""
    p = Path(path)
    if not p.is_file():
        raise IngestionError(f"File not found: {p.name}")
    return load_bytes(p.read_bytes(), p.name, config)

