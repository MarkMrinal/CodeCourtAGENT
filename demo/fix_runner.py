"""
Execution engine for Phase 3.5 Guided Fix Demo.
Coordinates vulnerability verification, patch application, and pytest execution.
"""
import difflib
import os
import subprocess
import sys
import sqlite3
import importlib
from typing import Dict, Any


def get_diff() -> str:
    """Generates a color-friendly unified diff between snippet.py and fallback_patch.py."""
    demo_dir = os.path.dirname(os.path.abspath(__file__))
    orig_path = os.path.join(demo_dir, "snippet.py")
    patch_path = os.path.join(demo_dir, "fallback_patch.py")

    with open(orig_path, "r", encoding="utf-8") as f:
        orig_lines = f.readlines()
    with open(patch_path, "r", encoding="utf-8") as f:
        patch_lines = f.readlines()

    diff = difflib.unified_diff(
        orig_lines,
        patch_lines,
        fromfile="demo/snippet.py (vulnerable)",
        tofile="demo/snippet.py (patched)",
        lineterm=""
    )
    return "\n".join(diff)


def run_in_process_test() -> Dict[str, Any]:
    """In-process test runner fallback if pytest or subprocess is unavailable."""
    from demo import snippet
    importlib.reload(snippet)

    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, email TEXT, role TEXT)")
    cursor.execute("INSERT INTO users VALUES (1, 'alice', 'alice@corp.internal', 'admin')")
    cursor.execute("INSERT INTO users VALUES (2, 'bob', 'bob@corp.internal', 'user')")
    cursor.execute("INSERT INTO users VALUES (3, 'eve', 'eve@corp.internal', 'auditor')")
    conn.commit()

    logs = ["Running in-process security verification suite:"]
    passed = True

    try:
        res1 = snippet.get_user_records(conn, "alice")
        assert len(res1) == 1 and res1[0][1] == "alice"
        logs.append("  PASS: test_normal_lookup — legitimate user query resolved correctly.")
    except Exception as e:
        passed = False
        logs.append(f"  FAIL: test_normal_lookup — {e}")

    try:
        res2 = snippet.get_user_records(conn, "' OR '1'='1")
        if len(res2) != 0:
            raise AssertionError(f"CRITICAL VULNERABILITY! SQL Injection leaked {len(res2)} unauthorized rows!")
        logs.append("  PASS: test_sql_injection_defense — malicious payload safely neutralized (0 rows leaked).")
    except Exception as e:
        passed = False
        logs.append(f"  FAIL: test_sql_injection_defense — {e}")

    conn.close()
    return {
        "exit_code": 0 if passed else 1,
        "passed": passed,
        "stdout": "\n".join(logs),
        "stderr": "",
    }


def run_demo_test() -> Dict[str, Any]:
    """Runs pytest on snippet_test.py and returns output + exit code, with fallback to in-process test."""
    try:
        demo_dir = os.path.dirname(os.path.abspath(__file__))
        test_file = os.path.join(demo_dir, "snippet_test.py")

        cmd = [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"]
        root_dir = os.path.abspath(os.path.join(demo_dir, ".."))
        result = subprocess.run(cmd, cwd=root_dir, capture_output=True, text=True, timeout=8)

        if result.returncode in (0, 1):
            return {
                "exit_code": result.returncode,
                "passed": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
    except Exception:
        pass

    return run_in_process_test()


def execute_guided_fix() -> Dict[str, Any]:
    """
    Complete end-to-end execution of Phase 3.5:
    1. Tests vulnerable snippet (verifies it fails)
    2. Swaps in patched code
    3. Tests patched snippet (verifies it passes)
    4. Restores original vulnerable snippet so demo is repeatable
    5. Returns test logs and unified diff
    """
    demo_dir = os.path.dirname(os.path.abspath(__file__))
    snippet_file = os.path.join(demo_dir, "snippet.py")
    patch_file = os.path.join(demo_dir, "fallback_patch.py")

    # Read original
    with open(snippet_file, "r", encoding="utf-8") as f:
        original_code = f.read()

    with open(patch_file, "r", encoding="utf-8") as f:
        patched_code = f.read()

    # Step 1: Run before test
    before_result = run_demo_test()

    # Step 2: Apply patch
    with open(snippet_file, "w", encoding="utf-8") as f:
        f.write(patched_code)

    # Step 3: Run after test
    try:
        after_result = run_demo_test()
    finally:
        # Step 4: Always restore original file so the demo remains reusable
        with open(snippet_file, "w", encoding="utf-8") as f:
            f.write(original_code)

    # Step 5: Compute diff
    diff_text = get_diff()

    return {
        "before": before_result,
        "after": after_result,
        "diff": diff_text,
        "success": (not before_result["passed"]) and after_result["passed"],
    }
