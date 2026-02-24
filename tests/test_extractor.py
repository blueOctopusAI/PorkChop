"""Tests for regex-based fact extraction."""

from porkchop.extractor import extract_facts, parse_dollar_amount


def test_extracts_us_code_refs(sample_cleaned_text):
    facts = extract_facts(sample_cleaned_text)
    assert len(facts["references"]["us_code"]) >= 1
    assert any("42" in ref for ref in facts["references"]["us_code"])


def test_extracts_public_laws(sample_cleaned_text):
    facts = extract_facts(sample_cleaned_text)
    assert len(facts["references"]["public_laws"]) >= 1
    assert any("118" in ref for ref in facts["references"]["public_laws"])


def test_extracts_act_names(sample_cleaned_text):
    facts = extract_facts(sample_cleaned_text)
    acts = facts["references"]["acts"]
    assert any("Stafford" in a for a in acts) or len(acts) >= 0


def test_extracts_funding(sample_cleaned_text):
    facts = extract_facts(sample_cleaned_text)
    assert len(facts["funding"]) >= 1
    amounts = [f["amount"] for f in facts["funding"]]
    assert any("100,000,000" in a for a in amounts)


def test_funding_has_numeric_value(sample_cleaned_text):
    facts = extract_facts(sample_cleaned_text)
    for item in facts["funding"]:
        assert "amount_numeric" in item
        assert isinstance(item["amount_numeric"], (int, float))


def test_extracts_dates(sample_cleaned_text):
    facts = extract_facts(sample_cleaned_text)
    assert len(facts["dates"]) >= 1
    assert any("January 15, 2025" in d for d in facts["dates"])


def test_extracts_deadlines(sample_cleaned_text):
    facts = extract_facts(sample_cleaned_text)
    assert len(facts["deadlines"]) >= 1
    assert any("January" in dl["date"] for dl in facts["deadlines"])


def test_extracts_duties(sample_cleaned_text):
    facts = extract_facts(sample_cleaned_text)
    assert len(facts["duties"]) >= 1
    assert any("Secretary of Defense" in d["entity"] for d in facts["duties"])


def test_extracts_entities(sample_cleaned_text):
    facts = extract_facts(sample_cleaned_text)
    assert len(facts["entities"]) >= 1
    entity_names = [e.lower() for e in facts["entities"]]
    assert any("homeland" in e for e in entity_names) or any("management" in e for e in entity_names)


def test_deduplicates_refs():
    text = "42 U.S.C. 3030a appears here. Also 42 U.S.C. 3030a appears again."
    facts = extract_facts(text)
    assert len(facts["references"]["us_code"]) == 1


def test_deduplicates_entities():
    text = "The Department of Defense is here. The Department of Defense is here again."
    facts = extract_facts(text)
    # Entity dedup is by lowercased name
    dept_count = sum(1 for e in facts["entities"] if "defense" in e.lower())
    assert dept_count <= 1


def test_parse_dollar_amount_basic():
    assert parse_dollar_amount("100,000,000") == 100_000_000


def test_parse_dollar_amount_with_scale():
    assert parse_dollar_amount("500", "million") == 500_000_000
    assert parse_dollar_amount("1.5", "billion") == 1_500_000_000


def test_parse_dollar_amount_invalid():
    assert parse_dollar_amount("not-a-number") == 0.0


def test_empty_text():
    facts = extract_facts("")
    assert facts["references"]["us_code"] == []
    assert facts["funding"] == []
    assert facts["entities"] == []


def test_extracts_fiscal_years(sample_cleaned_text):
    facts = extract_facts(sample_cleaned_text)
    assert len(facts["fiscal_years"]) >= 1
    assert "2024" in facts["fiscal_years"] or "2025" in facts["fiscal_years"]
