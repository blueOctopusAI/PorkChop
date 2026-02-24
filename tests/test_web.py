"""Tests for Flask web frontend."""

import tempfile
from pathlib import Path

import pytest

from porkchop.database import Database
from porkchop.web.app import create_app


@pytest.fixture
def app():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        app = create_app(str(db_path))
        app.config["TESTING"] = True
        # Seed some data
        db = Database(db_path)
        bill_id = db.upsert_bill(118, "hr", 10515, title="Test Appropriations Act")
        db.add_spending_item(bill_id, "$100M", amount_numeric=100_000_000, purpose="disaster relief")
        db.add_reference(bill_id, "us_code", "42 U.S.C. 3030a")
        db.add_summary(bill_id, "This bill provides disaster relief funding.")
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_index(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"PorkChop" in resp.data


def test_index_shows_bills(client):
    resp = client.get("/")
    assert b"Test Appropriations Act" in resp.data


def test_bill_detail(client):
    resp = client.get("/bill/1")
    assert resp.status_code == 200
    assert b"HR 10515" in resp.data
    assert b"disaster relief" in resp.data


def test_bill_not_found(client):
    resp = client.get("/bill/999")
    assert resp.status_code == 404


def test_spending_page(client):
    resp = client.get("/bill/1/spending")
    assert resp.status_code == 200
    assert b"100" in resp.data


def test_compare_page(client):
    resp = client.get("/bill/1/compare")
    assert resp.status_code == 200


def test_search_page(client):
    resp = client.get("/search?q=Appropriations")
    assert resp.status_code == 200
    assert b"Test Appropriations Act" in resp.data


def test_search_empty(client):
    resp = client.get("/search?q=nonexistent")
    assert resp.status_code == 200
    assert b"0 result" in resp.data


def test_api_bills(client):
    resp = client.get("/api/bills")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) >= 1


def test_api_bill_detail(client):
    resp = client.get("/api/bills/1")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["title"] == "Test Appropriations Act"
    assert data["total_spending"] == 100_000_000


def test_api_bill_not_found(client):
    resp = client.get("/api/bills/999")
    assert resp.status_code == 404


def test_api_spending(client):
    resp = client.get("/api/bills/1/spending")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 100_000_000


def test_api_search(client):
    resp = client.get("/api/search?q=Appropriations")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) >= 1


def test_api_search_missing_query(client):
    resp = client.get("/api/search")
    assert resp.status_code == 400


def test_api_stats(client):
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["bills_analyzed"] >= 1
