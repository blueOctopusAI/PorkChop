"""Tests for text cleaning module."""

from porkchop.cleaner import clean_text


def test_removes_verdate_lines(sample_raw_text):
    result = clean_text(sample_raw_text)
    assert "VerDate" not in result


def test_removes_jkt_lines(sample_raw_text):
    result = clean_text(sample_raw_text)
    assert "Jkt" not in result


def test_removes_windows_paths(sample_raw_text):
    result = clean_text(sample_raw_text)
    assert "C:\\USERS" not in result
    assert "I:\\FY25" not in result


def test_removes_xml_references(sample_raw_text):
    result = clean_text(sample_raw_text)
    assert ".xml" not in result
    assert "(955033|8)" not in result


def test_removes_timestamps(sample_raw_text):
    result = clean_text(sample_raw_text)
    assert "(5:46 p.m.)" not in result


def test_removes_leading_line_numbers(sample_raw_text):
    result = clean_text(sample_raw_text)
    # Lines like "1 DIVISION A" should become "DIVISION A"
    assert "DIVISION A" in result
    # Should not start with a standalone digit+space
    for line in result.split("\n"):
        stripped = line.strip()
        if stripped and stripped[0].isdigit():
            # Could be a section number like "101." which is fine
            assert not stripped.split()[0].isdigit() or "SEC" in stripped or "$" in stripped or "U.S.C." in stripped


def test_preserves_us_code_references(sample_raw_text):
    result = clean_text(sample_raw_text)
    assert "42 U.S.C." in result or "U.S.C." in result


def test_preserves_dollar_amounts(sample_raw_text):
    result = clean_text(sample_raw_text)
    assert "$100,000,000" in result
    assert "$500,000,000" in result


def test_preserves_public_law_refs(sample_raw_text):
    result = clean_text(sample_raw_text)
    assert "Public Law" in result


def test_preserves_division_markers(sample_raw_text):
    result = clean_text(sample_raw_text)
    assert "DIVISION A" in result


def test_preserves_title_markers(sample_raw_text):
    result = clean_text(sample_raw_text)
    assert "TITLE I" in result


def test_normalizes_whitespace():
    text = "too    many     spaces    here"
    result = clean_text(text)
    assert "  " not in result


def test_removes_excessive_blank_lines():
    text = "line one\n\n\n\n\nline two"
    result = clean_text(text)
    # Phase 2 strips empty lines, Phase 3 normalizes remaining blanks
    assert "\n\n\n" not in result
    assert "line one" in result
    assert "line two" in result


def test_empty_input():
    assert clean_text("") == ""


def test_preserves_entity_names(sample_raw_text):
    result = clean_text(sample_raw_text)
    assert "Department of Homeland Security" in result
    assert "Office of Management and Budget" in result


def test_preserves_act_names(sample_raw_text):
    result = clean_text(sample_raw_text)
    assert "Stafford Disaster Relief" in result
