"""Tests for pork scoring heuristics (no API calls)."""

from porkchop.scorer import heuristic_score


def test_clean_spending_scores_low():
    item = {
        "purpose": "national defense operations",
        "recipient": "Department of Defense",
        "amount_numeric": 500_000_000,
        "source_text": "$500,000,000 for national defense operations",
    }
    result = heuristic_score(item, bill_title="National Defense Authorization Act")
    assert result["score"] < 30


def test_earmark_spending_scores_high():
    item = {
        "purpose": "construction of the John Smith Memorial Bridge located in Springfield County",
        "recipient": "Springfield County Department of Transportation",
        "amount_numeric": 5_000_000,
        "source_text": "$5,000,000 for construction of the John Smith Memorial Bridge located in Springfield County",
    }
    result = heuristic_score(item, bill_title="National Defense Authorization Act")
    assert result["score"] >= 40
    assert "earmark_signals" in " ".join(result["flags"])


def test_geographic_specificity_flagged():
    item = {
        "purpose": "road improvements in Johnson County",
        "recipient": "Johnson County",
        "amount_numeric": 2_000_000,
        "source_text": "$2,000,000 for road improvements in Johnson County",
    }
    result = heuristic_score(item, bill_title="Disaster Relief Act")
    assert "geographic_specificity" in result["flags"]


def test_named_entity_flagged():
    item = {
        "purpose": "research grant to University of Springfield",
        "recipient": "University of Springfield",
        "amount_numeric": 1_000_000,
        "source_text": "",
    }
    result = heuristic_score(item)
    assert "named_entity" in result["flags"]


def test_small_amount_flagged():
    item = {
        "purpose": "equipment purchase",
        "recipient": "some agency",
        "amount_numeric": 500_000,
        "source_text": "",
    }
    result = heuristic_score(item)
    assert "small_specific_amount" in result["flags"]


def test_unrelated_purpose_flagged():
    item = {
        "purpose": "museum renovation",
        "recipient": "National Arts Foundation",
        "amount_numeric": 3_000_000,
        "source_text": "$3,000,000 for museum renovation",
    }
    result = heuristic_score(item, bill_title="Military Construction Appropriations Act")
    assert "potentially_unrelated" in result["flags"]


def test_score_capped_at_100():
    item = {
        "purpose": "construction of memorial bridge located in county of Springfield for the university hospital foundation museum",
        "recipient": "Springfield County Foundation",
        "amount_numeric": 100_000,
        "source_text": "located in the county of Springfield for the university hospital foundation museum institute center for memorial bridge highway airport",
    }
    result = heuristic_score(item, bill_title="Unrelated Bill")
    assert result["score"] <= 100


def test_empty_item():
    result = heuristic_score({})
    assert result["score"] == 0
    assert result["flags"] == []


def test_method_is_heuristic():
    result = heuristic_score({"purpose": "test"})
    assert result["method"] == "heuristic"
