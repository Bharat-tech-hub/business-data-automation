import pytest

from src.ingestion import sanitize_filename


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("report.xlsx", "report.xlsx"),
        ("my file.csv", "my file.csv"),
        ("C:\\Users\\x\\data.csv", "data.csv"),
        ("../../etc/passwd", "passwd"),
        ("bad:name?.csv", "bad_name_.csv"),
        (".hidden", "hidden"),
        ("  spaced.csv  ", "spaced.csv"),
        ("r\u00e9sum\u00e9.csv", "r_sum_.csv"),
        ("", "upload"),
        (None, "upload"),
        ("...", "upload"),
        ("folder/", "upload"),
    ],
)
def test_sanitize_filename(raw, expected):
    assert sanitize_filename(raw) == expected