"""Tests for bill version comparison (no API calls)."""

from porkchop.comparator import text_diff, _split_sections, _extract_spending_lines


def test_text_diff_identical():
    result = text_diff("same text", "same text")
    assert result["additions_count"] == 0
    assert result["removals_count"] == 0
    assert result["similarity_ratio"] == 1.0


def test_text_diff_additions():
    result = text_diff("line one", "line one\nline two")
    assert result["additions_count"] >= 1


def test_text_diff_removals():
    result = text_diff("line one\nline two", "line one")
    assert result["removals_count"] >= 1


def test_text_diff_spending_detection():
    text_a = "The program receives $100,000,000 for operations."
    text_b = "The program receives $200,000,000 for operations."
    result = text_diff(text_a, text_b)
    assert len(result["spending_added"]) >= 1 or len(result["spending_removed"]) >= 1


def test_split_sections():
    text = """DIVISION A
Content of Division A

TITLE I
Content of Title I

SEC. 101
Content of Section 101"""
    sections = _split_sections(text)
    assert "DIVISION A" in sections
    assert "TITLE I" in sections


def test_extract_spending_lines():
    lines = [
        "$100,000,000 for disaster relief",
        "no money here",
        "$50 million for education",
    ]
    results = _extract_spending_lines(lines)
    assert len(results) >= 1
    assert any("100,000,000" in r["amount"] for r in results)


def test_text_diff_similarity():
    text_a = "The quick brown fox jumps over the lazy dog."
    text_b = "The quick brown cat jumps over the lazy dog."
    result = text_diff(text_a, text_b)
    assert 0 < result["similarity_ratio"] < 1


def test_empty_diff():
    result = text_diff("", "")
    assert result["additions_count"] == 0
    assert result["removals_count"] == 0
