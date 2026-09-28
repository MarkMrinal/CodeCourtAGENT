"""
Test suite proving SQL injection vulnerability and verifying secure fix.
"""
import sqlite3
import pytest

# Target module can be swapped or patched dynamically
from demo import snippet


@pytest.fixture
def test_db():
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, email TEXT, role TEXT)")
    cursor.execute("INSERT INTO users VALUES (1, 'alice', 'alice@corp.internal', 'admin')")
    cursor.execute("INSERT INTO users VALUES (2, 'bob', 'bob@corp.internal', 'user')")
    cursor.execute("INSERT INTO users VALUES (3, 'eve', 'eve@corp.internal', 'auditor')")
    conn.commit()
    yield conn
    conn.close()


def test_normal_lookup(test_db):
    """Verifies legitimate user lookup works."""
    results = snippet.get_user_records(test_db, "alice")
    assert len(results) == 1
    assert results[0][1] == "alice"


def test_sql_injection_defense(test_db):
    """
    Simulates SQL Injection payload: ' OR '1'='1
    In a secure implementation, searching for a non-existent literal username returns 0 rows.
    In the vulnerable snippet, all 3 rows are leaked!
    """
    malicious_input = "' OR '1'='1"
    results = snippet.get_user_records(test_db, malicious_input)
    
    # Must NOT leak all rows
    assert len(results) == 0, (
        f"CRITICAL VULNERABILITY DETECTED! Expected 0 records for non-existent username, "
        f"but got {len(results)} rows. SQL Injection succeeded!"
    )
