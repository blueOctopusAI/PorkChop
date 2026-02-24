"""Tests for bill ingestion (parsing only — no API calls)."""

from porkchop.ingestion import parse_bill_id, import_from_file

import tempfile
from pathlib import Path


def test_parse_hr_dash():
    congress, bill_type, number = parse_bill_id("HR-10515")
    assert bill_type == "hr"
    assert number == 10515


def test_parse_with_congress():
    congress, bill_type, number = parse_bill_id("118-HR-10515")
    assert congress == 118
    assert bill_type == "hr"
    assert number == 10515


def test_parse_lowercase():
    congress, bill_type, number = parse_bill_id("hr10515")
    assert bill_type == "hr"
    assert number == 10515


def test_parse_with_space():
    congress, bill_type, number = parse_bill_id("HR 10515")
    assert bill_type == "hr"
    assert number == 10515


def test_parse_senate():
    congress, bill_type, number = parse_bill_id("S-1234")
    assert bill_type == "s"
    assert number == 1234


def test_parse_joint_resolution():
    congress, bill_type, number = parse_bill_id("HJRES-100")
    assert bill_type == "hjres"
    assert number == 100


def test_parse_slash_format():
    congress, bill_type, number = parse_bill_id("118/hr/10515")
    assert congress == 118
    assert bill_type == "hr"
    assert number == 10515


def test_parse_invalid():
    import pytest
    with pytest.raises(ValueError):
        parse_bill_id("not-a-bill")


def test_import_from_file(tmp_db):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Sample bill text for testing.")
        f.flush()
        result = import_from_file(f.name, "HR-10515", db=tmp_db)

    assert result["congress"] == 118 or result["congress"] > 0
    assert result["bill_type"] == "hr"
    assert result["bill_number"] == 10515
    assert result["text"] == "Sample bill text for testing."
    assert result.get("db_id") is not None

    # Verify in database
    bill = tmp_db.get_bill(result["db_id"])
    assert bill is not None
