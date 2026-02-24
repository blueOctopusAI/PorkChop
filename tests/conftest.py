"""Shared test fixtures."""

import tempfile
from pathlib import Path

import pytest

from porkchop.database import Database


SAMPLE_RAW_TEXT = """VerDate Nov 24 2008 17:46 Dec 17, 2024 Jkt 000000 PO 00000 Frm 00001 Fmt 6652 Sfmt 6211
C:\\USERS\\KSALMON\\APPDATA\\ROAMING\\SOFTQUAD\\XMETAL\\11.0\\GEN\\C\\D121724.03
December 17, 2024 (5:46 p.m.)
I:\\FY25\\SUPPS\\D121724.038.XML
l:\\v7\\121724\\7121724.012.xml (955033|8)
1 DIVISION A—FURTHER CONTINUING
2 APPROPRIATIONS ACT, 2025
3 SEC. 101. (a) Such amounts as may be nec-
4 essary, at a rate for operations as provided in
5 the applicable appropriations Acts for fiscal
6 year 2024 and under the authority and condi-
7 tions provided in such Acts, for continuing
8 projects or activities (including the costs of
9 direct loans and loan guarantees) that are not
10 otherwise specifically provided for in this Act
11 TITLE I—DEPARTMENT OF DEFENSE
12 SEC. 102. The Secretary of Defense shall submit a report
13 to Congress not later than January 15, 2025.
14 $100,000,000 for disaster relief operations.
15 The Department of Homeland Security shall coordinate with
16 the Office of Management and Budget.
17 Pursuant to 42 U.S.C. 3030a and Public Law 118-42,
18 the Robert T. Stafford Disaster Relief and Emergency Assistance Act
19 authorizes $500,000,000 for FEMA operations until September 30, 2025.
"""

SAMPLE_CLEANED_TEXT = """DIVISION A—FURTHER CONTINUING
APPROPRIATIONS ACT, 2025
SEC. 101. (a) Such amounts as may be necessary, at a rate for operations as provided in the applicable appropriations Acts for fiscal year 2024 and under the authority and conditions provided in such Acts, for continuing projects or activities (including the costs of direct loans and loan guarantees) that are not otherwise specifically provided for in this Act
TITLE I—DEPARTMENT OF DEFENSE
SEC. 102. The Secretary of Defense shall submit a report to Congress not later than January 15, 2025.
$100,000,000 for disaster relief operations.
The Department of Homeland Security shall coordinate with the Office of Management and Budget.
Pursuant to 42 U.S.C. 3030a and Public Law 118-42, the Robert T. Stafford Disaster Relief and Emergency Assistance Act authorizes $500,000,000 for FEMA operations until September 30, 2025."""


@pytest.fixture
def tmp_db():
    """Create a temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        yield Database(db_path)


@pytest.fixture
def sample_raw_text():
    return SAMPLE_RAW_TEXT


@pytest.fixture
def sample_cleaned_text():
    return SAMPLE_CLEANED_TEXT


@pytest.fixture
def sample_bill(tmp_db):
    """Create a sample bill in the test database."""
    bill_id = tmp_db.upsert_bill(118, "hr", 10515, title="Test Bill")
    version_id = tmp_db.upsert_version(
        bill_id, "enr", version_name="Enrolled", raw_text=SAMPLE_CLEANED_TEXT
    )
    return {"bill_id": bill_id, "version_id": version_id, "db": tmp_db}
