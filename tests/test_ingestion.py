"""Tests for src.ingestion using tiny hand-built files."""

import io
import zipfile

import pandas as pd
import pytest

from config.settings import Settings
from src.ingestion import (
    CorruptFileError,
    EmptyFileError,
    FileTooLargeError,
    IngestionError,
    MissingColumnsError,
    UnsupportedFileTypeError,
    load_bytes,
    load_file,
    sanitize_filename,
)
from src.schema import REQUIRED_COLUMNS

HEADER = ",".join(REQUIRED_COLUMNS)
ROW1 = "536365,85123A,WHITE HEART,6,2010-12-01 08:26:00,2.55,17850,United Kingdom"
ROW2 = "C536379,D,Discount,-1,2010-12-01 09:41:00,27.50,14527,United Kingdom"
CSV_TEXT = f"{HEADER}\n{ROW1}\n{ROW2}\n"


def _xlsx_bytes(df: pd.DataFrame, extra_sheet: bool = False) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sales")
        if extra_sheet:
            df.to_excel(writer, index=False, sheet_name="Other")
    return buffer.getvalue()


def _df() -> pd.DataFrame:
    return pd.DataFrame(
        [["536365", "85123A", "WHITE HEART", 6, "2010-12-01", 2.55, 17850, "United Kingdom"]],
        columns=list(REQUIRED_COLUMNS),
    )


def test_valid_csv_loads_with_expected_counts():
    df, res = load_bytes(CSV_TEXT.encode(), "sales.csv")
    assert df.shape == (2, 8)
    assert (res.rows, res.columns, res.file_format) == (2, 8, "csv")
    assert res.encoding == "utf-8-sig"
    assert res.warnings == []


def test_csv_ids_are_kept_as_text():
    df, _ = load_bytes(CSV_TEXT.encode(), "sales.csv")
    assert df["InvoiceNo"].tolist() == ["536365", "C536379"]
    assert df["CustomerID"].tolist() == ["17850", "14527"]


def test_valid_xlsx_loads():
    df, res = load_bytes(_xlsx_bytes(_df()), "sales.xlsx")
    assert df.shape == (1, 8)
    assert res.file_format == "xlsx"


def test_xlsx_extra_sheet_gives_warning():
    _, res = load_bytes(_xlsx_bytes(_df(), extra_sheet=True), "sales.xlsx")
    assert any("2 sheets" in w for w in res.warnings)


def test_unsupported_extension_rejected():
    with pytest.raises(UnsupportedFileTypeError):
        load_bytes(b"data", "malware.exe")


def test_double_extension_rejected():
    with pytest.raises(UnsupportedFileTypeError):
        load_bytes(CSV_TEXT.encode(), "sales.csv.exe")


def test_empty_bytes_rejected():
    with pytest.raises(EmptyFileError):
        load_bytes(b"", "sales.csv")


def test_header_only_csv_rejected():
    with pytest.raises(EmptyFileError):
        load_bytes(f"{HEADER}\n".encode(), "sales.csv")


def test_oversized_file_rejected():
    cfg = Settings(max_upload_size_mb=1)
    with pytest.raises(FileTooLargeError):
        load_bytes(b"x" * (1024 * 1024 + 1), "sales.csv", cfg)


def test_fake_xlsx_rejected():
    with pytest.raises(CorruptFileError):
        load_bytes(b"this is plain text, not a zip", "sales.xlsx")


def test_zip_without_workbook_rejected():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("hello.txt", "hi")
    with pytest.raises(CorruptFileError):
        load_bytes(buffer.getvalue(), "sales.xlsx")


def test_binary_csv_rejected():
    with pytest.raises(CorruptFileError):
        load_bytes(b"a,b\x00c\n1,2\n", "sales.csv")


def test_missing_column_named_in_error():
    bad = CSV_TEXT.replace("Country", "Land")
    with pytest.raises(MissingColumnsError, match="Country"):
        load_bytes(bad.encode(), "sales.csv")


def test_header_whitespace_is_trimmed():
    spaced = CSV_TEXT.replace("Quantity", " Quantity ")
    df, _ = load_bytes(spaced.encode(), "sales.csv")
    assert "Quantity" in df.columns


def test_extra_column_gives_warning():
    text = f"{HEADER},Notes\n{ROW1},hello\n"
    df, res = load_bytes(text.encode(), "sales.csv")
    assert "Notes" in df.columns
    assert any("Notes" in w for w in res.warnings)


def test_latin1_csv_decoded_with_warning():
    text = CSV_TEXT.replace("WHITE HEART", "CAF\u00c9 MUG")
    df, res = load_bytes(text.encode("latin-1"), "sales.csv")
    assert res.encoding == "latin-1"
    assert df["Description"].iloc[0] == "CAF\u00c9 MUG"
    assert any("Latin-1" in w for w in res.warnings)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("sales.csv", "sales.csv"),
        ("../../etc/passwd.csv", "passwd.csv"),
        ("C:\\Users\\x\\data.csv", "data.csv"),
        ("my data!.csv", "my data_.csv"),
        ("", "upload"),
        (".hidden.csv", "hidden.csv"),
    ],
)
def test_sanitize_filename(raw, expected):
    assert sanitize_filename(raw) == expected


def test_load_file_reads_without_modifying(tmp_path):
    path = tmp_path / "sales.csv"
    path.write_text(CSV_TEXT, encoding="utf-8")
    before = path.read_bytes()
    df, res = load_file(path)
    assert df.shape == (2, 8)
    assert res.file_name == "sales.csv"
    assert path.read_bytes() == before


def test_load_file_missing_path(tmp_path):
    with pytest.raises(IngestionError):
        load_file(tmp_path / "nope.csv")
