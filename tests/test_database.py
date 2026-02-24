"""Tests for SQLite database operations."""


def test_create_db(tmp_db):
    assert tmp_db.db_path.exists()


def test_upsert_bill(tmp_db):
    bill_id = tmp_db.upsert_bill(118, "hr", 10515, title="Test Bill")
    assert bill_id > 0


def test_upsert_bill_idempotent(tmp_db):
    id1 = tmp_db.upsert_bill(118, "hr", 10515, title="Version 1")
    id2 = tmp_db.upsert_bill(118, "hr", 10515, title="Version 2")
    assert id1 == id2


def test_get_bill(tmp_db):
    tmp_db.upsert_bill(118, "hr", 10515, title="Test Bill")
    bill = tmp_db.find_bill(118, "hr", 10515)
    assert bill is not None
    assert bill["title"] == "Test Bill"


def test_list_bills(tmp_db):
    tmp_db.upsert_bill(118, "hr", 1, title="Bill 1")
    tmp_db.upsert_bill(118, "s", 2, title="Bill 2")
    bills = tmp_db.list_bills()
    assert len(bills) == 2


def test_search_bills(tmp_db):
    tmp_db.upsert_bill(118, "hr", 1, title="Disaster Relief Act")
    tmp_db.upsert_bill(118, "s", 2, title="Defense Authorization")
    results = tmp_db.search_bills("Disaster")
    assert len(results) == 1
    assert results[0]["title"] == "Disaster Relief Act"


def test_upsert_version(tmp_db):
    bill_id = tmp_db.upsert_bill(118, "hr", 10515)
    v_id = tmp_db.upsert_version(bill_id, "enr", version_name="Enrolled")
    assert v_id > 0


def test_get_versions(tmp_db):
    bill_id = tmp_db.upsert_bill(118, "hr", 10515)
    tmp_db.upsert_version(bill_id, "ih", version_name="Introduced")
    tmp_db.upsert_version(bill_id, "enr", version_name="Enrolled")
    versions = tmp_db.get_versions(bill_id)
    assert len(versions) == 2


def test_add_section(tmp_db):
    bill_id = tmp_db.upsert_bill(118, "hr", 10515)
    sec_id = tmp_db.add_section(bill_id, "Section text here", section_number="101")
    assert sec_id > 0
    sections = tmp_db.get_sections(bill_id)
    assert len(sections) == 1


def test_add_spending_item(tmp_db):
    bill_id = tmp_db.upsert_bill(118, "hr", 10515)
    tmp_db.add_spending_item(bill_id, "$100,000,000", amount_numeric=100_000_000, purpose="disaster relief")
    spending = tmp_db.get_spending(bill_id)
    assert len(spending) == 1
    assert spending[0]["amount"] == "$100,000,000"


def test_total_spending(tmp_db):
    bill_id = tmp_db.upsert_bill(118, "hr", 10515)
    tmp_db.add_spending_item(bill_id, "$100M", amount_numeric=100_000_000)
    tmp_db.add_spending_item(bill_id, "$50M", amount_numeric=50_000_000)
    assert tmp_db.get_total_spending(bill_id) == 150_000_000


def test_add_reference(tmp_db):
    bill_id = tmp_db.upsert_bill(118, "hr", 10515)
    tmp_db.add_reference(bill_id, "us_code", "42 U.S.C. 3030a")
    refs = tmp_db.get_references(bill_id)
    assert len(refs) == 1


def test_add_deadline(tmp_db):
    bill_id = tmp_db.upsert_bill(118, "hr", 10515)
    tmp_db.add_deadline(bill_id, date="January 15, 2025", action="Submit report")
    dls = tmp_db.get_deadlines(bill_id)
    assert len(dls) == 1


def test_add_entity(tmp_db):
    bill_id = tmp_db.upsert_bill(118, "hr", 10515)
    tmp_db.add_entity(bill_id, "Department of Defense", entity_type="department")
    entities = tmp_db.get_entities(bill_id)
    assert len(entities) == 1


def test_add_summary(tmp_db):
    bill_id = tmp_db.upsert_bill(118, "hr", 10515)
    tmp_db.add_summary(bill_id, "This bill does things.", model_used="test")
    assert tmp_db.get_bill_summary(bill_id) == "This bill does things."


def test_pork_scores(tmp_db):
    bill_id = tmp_db.upsert_bill(118, "hr", 10515)
    si_id = tmp_db.add_spending_item(bill_id, "$1M", amount_numeric=1_000_000)
    tmp_db.add_pork_score(bill_id, si_id, 75, reasons="suspicious")
    scores = tmp_db.get_pork_scores(bill_id)
    assert len(scores) == 1
    assert scores[0]["score"] == 75
    summary = tmp_db.get_bill_pork_summary(bill_id)
    assert summary["avg_score"] == 75


def test_stats(tmp_db):
    bill_id = tmp_db.upsert_bill(118, "hr", 10515)
    tmp_db.add_spending_item(bill_id, "$1M", amount_numeric=1_000_000)
    stats = tmp_db.get_stats()
    assert stats["bills_analyzed"] == 1
    assert stats["spending_items"] == 1
    assert stats["total_spending"] == 1_000_000


def test_clear_bill_data(tmp_db):
    bill_id = tmp_db.upsert_bill(118, "hr", 10515)
    tmp_db.add_section(bill_id, "text")
    tmp_db.add_spending_item(bill_id, "$1M", amount_numeric=1_000_000)
    tmp_db.add_reference(bill_id, "us_code", "test ref")
    tmp_db.clear_bill_data(bill_id)
    assert len(tmp_db.get_sections(bill_id)) == 0
    assert len(tmp_db.get_spending(bill_id)) == 0
    assert len(tmp_db.get_references(bill_id)) == 0
    # Bill record itself should still exist
    assert tmp_db.get_bill(bill_id) is not None
