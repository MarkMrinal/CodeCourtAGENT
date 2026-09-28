"""
Basic unit tests for sample_project.
"""
import sqlite3
import pytest
from sample_project.billing import process_invoice_calculation


def test_invoice_calculation_us():
    result = process_invoice_calculation(100.0, "pro", "US", "", False)
    assert result == 104.0


def test_invoice_calculation_partner():
    result = process_invoice_calculation(100.0, "standard", "CA", "", True)
    assert result == 103.0
