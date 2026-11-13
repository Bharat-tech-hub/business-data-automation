"""Tests for src.cleaning using tiny hand-built frames."""

import pandas as pd
import pytest

import src.cleaning as cleaning
from src.cleaning import NO_DESCRIPTION, build_product_names, clean, save_processed
from src.schema import REQUIRED_COLUMNS


def row(invoice="500001", code="22423", desc="ITEM", qty=2, date="2011-01-05 10:00:00",
        price=1.5, cust=17850.0, country="United Kingdom"):
    return [invoice, code, desc, qty, date, price, cust, country]


def frame(rows):
    return pd.DataFrame(rows, columns=list(REQUIRED_COLUMNS))


def test_does_not_modify_input():
    df = frame([row(desc=" ITEM "), row(invoice="500002", code=85123)])
    before = df.copy()
    clean(df)
    pd.testing.assert_frame_equal(df, before)


def test_missing_required_column_raises():
    with pytest.raises(ValueError, match="Country"):
        clean(frame([row()]).drop(columns="Country"))


def test_customer_id_becomes_integer_text():
    out, _ = clean(frame([row(cust=17850.0), row(invoice="500002", cust=None)]))
    assert out["CustomerID"].tolist() == ["17850", ""]
    assert out["has_customer"].tolist() == [True, False]


def test_stockcode_text_and_uppercase_counted():
    out, rep = clean(frame([row(code=85123), row(invoice="500002", code="84872a"),
                            row(invoice="500003", code="84872A")]))
    assert out["StockCode"].tolist() == ["85123", "84872A", "84872A"]
    assert rep.get("uppercase_stockcode").affected == 1


def test_whitespace_counted_per_cell():
    _, rep = clean(frame([row(desc=" A "), row(invoice="500002", desc="B ")]))
    assert rep.get("strip_whitespace").affected == 2


def test_missing_description_filled():
    out, rep = clean(frame([row(desc=None), row(invoice="500002", desc="   ")]))
    assert out["Description"].tolist() == [NO_DESCRIPTION, NO_DESCRIPTION]
    assert rep.get("fill_missing_description").affected == 2


def test_unusable_rows_dropped_and_counted():
    out, rep = clean(frame([row(), row(invoice="500002", date="bad"),
                            row(invoice="500003", qty="abc"), row(invoice="500004", price=None)]))
    assert len(out) == 1
    assert rep.get("drop_unusable_rows").affected == 3
    assert rep.rows_in == 4 and rep.rows_out == 1


def test_exact_duplicates_removed():
    out, rep = clean(frame([row(), row(), row(invoice="500002")]))
    assert len(out) == 2
    assert rep.get("remove_duplicates").affected == 1


def test_duplicates_found_after_normalisation():
    out, rep = clean(frame([row(desc="ITEM"), row(desc=" ITEM ")]))
    assert len(out) == 1
    assert rep.get("remove_duplicates").affected == 1


def test_duplicates_kept_when_switch_off(monkeypatch):
    monkeypatch.setattr(cleaning, "REMOVE_DUPLICATES", False)
    out, rep = clean(frame([row(), row()]))
    assert len(out) == 2
    assert rep.get("remove_duplicates").affected == 0


def test_flags_and_line_total():
    out, _ = clean(frame([
        row(invoice="500001", qty=3, price=2.0),
        row(invoice="C500002", qty=-1, price=2.0),
        row(invoice="500003", code="POST", qty=1, price=18.0),
        row(invoice="500004", qty=1, price=0.0),
        row(invoice="500005", code="gift_0001_20", qty=1, price=16.67),
        row(invoice="500006", qty=-5, price=0.0),
    ]))
    assert out["is_cancelled"].tolist() == [False, True, False, False, False, False]
    assert out["is_product"].tolist() == [True, True, False, True, False, True]
    assert out["is_sale"].tolist() == [True, False, False, False, False, False]
    assert out["LineTotal"].tolist() == [6.0, -2.0, 18.0, 0.0, 16.67, -0.0]


def test_invoice_month():
    out, _ = clean(frame([row(date="2011-03-31 23:59:00"), row(invoice="500002", date="2011-04-01 00:00:00")]))
    assert out["InvoiceMonth"].tolist() == ["2011-03", "2011-04"]


def test_product_names_most_frequent_then_alphabetical():
    out, _ = clean(frame([
        row(invoice="500001", desc="B NAME"), row(invoice="500002", desc="A NAME"),
        row(invoice="500003", desc="A NAME"), row(invoice="500004", code="99999", desc="Y"),
        row(invoice="500005", code="99999", desc="X"), row(invoice="500006", code="11111", desc=None),
    ]))
    names = build_product_names(out)
    assert names["22423"] == "A NAME"
    assert names["99999"] == "X"
    assert "11111" not in names.index


def test_audit_trail_has_all_steps():
    _, rep = clean(frame([row()]))
    assert list(rep.to_frame()["step"]) == [
        "strip_whitespace", "uppercase_stockcode", "drop_unusable_rows",
        "fill_missing_description", "remove_duplicates", "flags_added",
    ]


def test_save_processed_roundtrip(tmp_path):
    out, _ = clean(frame([row(), row(invoice="500002")]))
    path = save_processed(out, tmp_path / "sub" / "clean.csv")
    assert path.is_file()
    assert len(pd.read_csv(path, dtype=str)) == 2
