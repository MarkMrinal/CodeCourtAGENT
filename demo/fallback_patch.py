"""
Secure patched version of snippet.py for Phase 3.5 Guided Fix Demo.
Uses parameterized queries with SQLite placeholders to eliminate SQL injection.
"""
import sqlite3


def get_user_records(db_connection: sqlite3.Connection, username_query: str):
    """
    SECURE: Uses parameterized query (?) to safely bind untrusted input.
    Neutralizes SQL injection attacks completely.
    """
    cursor = db_connection.cursor()
    query = "SELECT id, username, email, role FROM users WHERE username = ?"
    cursor.execute(query, (username_query,))
    return cursor.fetchall()
