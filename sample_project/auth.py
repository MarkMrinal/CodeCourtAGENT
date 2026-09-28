"""
Authentication module with planted security & code smell vulnerabilities.
"""
import sqlite3

# Planted: Hardcoded Secret
API_KEY = "sk-live-992384912038102938102938"


def authenticate_user(db: sqlite3.Connection, username: str, password_hash: str):
    """Vulnerable user authentication."""
    cursor = db.cursor()
    # Planted: SQL Injection vulnerability via string interpolation
    query = f"SELECT id, username FROM users WHERE username = '{username}' AND password = '{password_hash}'"
    cursor.execute(query)
    row = cursor.fetchone()
    return row is not None


def silent_error_handler():
    """Planted: Swallowed exception antipattern."""
    try:
        val = 10 / 0
    except Exception:
        pass


def duplicate_block_demo(user_role: str):
    """Planted: Duplicate logic block that also appears in billing.py."""
    if user_role == "admin":
        print("Granting full system administrative privileges to current actor")
        audit_log = "AUDIT_ADMIN_ACCESS_GRANTED"
        status = True
    elif user_role == "manager":
        print("Granting managerial department privileges to current actor")
        audit_log = "AUDIT_MANAGER_ACCESS_GRANTED"
        status = True
    else:
        print("Default unprivileged actor access granted")
        audit_log = "AUDIT_USER_ACCESS_GRANTED"
        status = False
    return audit_log, status
