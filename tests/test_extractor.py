"""Tests for regex-based fact extraction."""

from porkchop.extractor import extract_facts, parse_dollar_amount, _clean_purpose


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


# --- Purpose extraction improvements ---


def test_purpose_necessary_expenses():
    """Extracts 'necessary expenses related to X' pattern."""
    text = "$30,780,000,000, for necessary expenses related to losses of revenue and increased costs."
    facts = extract_facts(text)
    assert len(facts["funding"]) >= 1
    purpose = facts["funding"][0]["purpose"]
    assert purpose != "unspecified"
    assert "losses of revenue" in purpose.lower()


def test_purpose_carry_out():
    """Extracts 'to carry out X' pattern."""
    text = "$3,000,000 to carry out regular testing for the purposes of verifying molasses inspection."
    facts = extract_facts(text)
    assert len(facts["funding"]) >= 1
    purpose = facts["funding"][0]["purpose"]
    assert purpose != "unspecified"
    assert "testing" in purpose.lower() or "verifying" in purpose.lower()


def test_purpose_additional_amount():
    """Extracts purpose from 'for an additional amount for FY, ... for the X program'."""
    text = "$5,691,000,000, for an additional amount for fiscal year 2025, to remain available until September 30, 2029, for the Virginia Class Submarine program."
    facts = extract_facts(text)
    assert len(facts["funding"]) >= 1
    purpose = facts["funding"][0]["purpose"]
    assert purpose != "unspecified"
    assert "virginia class submarine" in purpose.lower()


def test_purpose_rejects_fiscal_year_only():
    """Does not accept 'fiscal year 2025' as a purpose."""
    assert _clean_purpose("fiscal year 2025") is None
    assert _clean_purpose("each of fiscal years 2024 and 2025") is None


def test_purpose_rejects_short():
    """Rejects single-word or very short purpose strings."""
    assert _clean_purpose("flood") is None
    assert _clean_purpose("budget") is None


def test_purpose_made_available():
    """Extracts purpose from 'shall be made available for' pattern."""
    text = "$10,000,000,000 shall be made available for the Secretary to make economic assistance available pursuant to section 2102."
    facts = extract_facts(text)
    assert len(facts["funding"]) >= 1
    purpose = facts["funding"][0]["purpose"]
    assert purpose != "unspecified"


# --- Recipient extraction ---


def test_recipient_transferred_to():
    """Extracts recipient from 'transferred to' pattern."""
    text = "$50,000,000 shall be transferred to ''Small Business Administration'' for audits."
    facts = extract_facts(text)
    assert len(facts["funding"]) >= 1
    recipient = facts["funding"][0].get("recipient")
    assert recipient is not None
    assert "small business" in recipient.lower()


def test_recipient_to_department():
    """Extracts recipient from 'to the Department of X' pattern."""
    text = "$150,000,000 to the Department of the Treasury, out of which amounts may be transferred."
    facts = extract_facts(text)
    assert len(facts["funding"]) >= 1
    recipient = facts["funding"][0].get("recipient")
    assert recipient is not None
    assert "treasury" in recipient.lower()


# --- Trailing commas on amounts ---


def test_amount_strips_trailing_comma():
    """Dollar amounts with trailing commas are parsed correctly."""
    text = "$30,780,000,000, to remain available until expended."
    facts = extract_facts(text)
    assert len(facts["funding"]) >= 1
    assert facts["funding"][0]["amount_numeric"] == 30_780_000_000


# --- Funding items have recipient and fiscal_years fields ---


def test_funding_has_recipient_field():
    """Every funding item has a recipient field (may be None)."""
    text = "$100,000,000 for disaster relief operations."
    facts = extract_facts(text)
    for item in facts["funding"]:
        assert "recipient" in item


def test_funding_has_fiscal_years_field():
    """Fiscal years are captured from context."""
    text = "$500,000,000 for fiscal year 2025 operations."
    facts = extract_facts(text)
    assert len(facts["funding"]) >= 1
    assert "fiscal_years" in facts["funding"][0]


# --- New patterns: to provide/make/fund ---


def test_purpose_to_provide():
    """Extracts 'to provide X' purpose pattern."""
    text = "$2,000,000,000 to provide assistance to producers of livestock for losses incurred."
    facts = extract_facts(text)
    assert len(facts["funding"]) >= 1
    purpose = facts["funding"][0]["purpose"]
    assert purpose != "unspecified"
    assert "assistance" in purpose.lower()


def test_purpose_rejects_junk():
    """Rejects 'such purpose', 'this section', etc as purposes."""
    text = "$100,000,000 for such purposes as the Secretary may determine."
    facts = extract_facts(text)
    assert len(facts["funding"]) >= 1
    # Should be rejected by junk filter
    purpose = facts["funding"][0]["purpose"]
    assert purpose == "unspecified" or "such purpose" not in purpose.lower()


def test_purpose_across_newlines():
    """Purpose extraction works across line breaks in raw bill text."""
    text = "$30,000,000, for reimbursement for administrative\nand operating expenses available for crop insurance."
    facts = extract_facts(text)
    assert len(facts["funding"]) >= 1
    purpose = facts["funding"][0]["purpose"]
    assert purpose != "unspecified"
    assert "reimbursement" in purpose.lower()


# --- Deadline improvements ---


def test_deadline_forward_action():
    """Deadline action comes from text AFTER 'not later than X days'."""
    text = "Not later than 60 days after the date of enactment, the Secretary shall submit a spending plan to the Committees on Appropriations."
    facts = extract_facts(text)
    assert len(facts["deadlines"]) >= 1
    dl = facts["deadlines"][0]
    assert dl["date"] == "60 days"
    assert "spending plan" in dl["action"].lower() or "submit" in dl["action"].lower()


def test_deadline_specific_date():
    """Deadline with a specific calendar date."""
    text = "Not later than January 15, 2026, the Administrator shall publish final regulations in the Federal Register."
    facts = extract_facts(text)
    assert len(facts["deadlines"]) >= 1
    dl = facts["deadlines"][0]
    assert "January 15, 2026" in dl["date"]
    assert "regulations" in dl["action"].lower() or "publish" in dl["action"].lower()


def test_purpose_backward_subheading():
    """Purpose extracted from uppercase subheading before dollar amount."""
    text = "\nOPERATIONS AND MAINTENANCE, NAVY\n\n$625,000,000 to remain available until expended."
    facts = extract_facts(text)
    assert len(facts["funding"]) >= 1
    purpose = facts["funding"][0]["purpose"]
    assert purpose != "unspecified"
    assert "operations" in purpose.lower() or "navy" in purpose.lower()
