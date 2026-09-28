"""
Vulnerable snippet for Phase 3.5 Guided Fix Demo.
Demonstrates a direct SQL injection vulnerability via string interpolation.
"""
import sqlite3


def get_user_records(db_connection: sqlite3.Connection, username_query: str):
    """
    VULNERABLE: Direct f-string interpolation into SQL statement.
    An attacker providing "' OR '1'='1" bypasses filter and leaks all records.
    """
    cursor = db_connection.cursor()
    # SQL Injection risk
    query = f"SELECT id, username, email, role FROM users WHERE username = '{username_query}'"
    cursor.execute(query)
    return cursor.fetchall()
