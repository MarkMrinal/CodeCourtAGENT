"""
Billing module with planted complexity, long function, and duplicate logic.
"""


def process_invoice_calculation(amount: float, tier: str, country: str, discount_code: str, is_partner: bool):
    """
    Planted: High Cyclomatic Complexity (> 10) and long function (> 35 lines).
    """
    tax_rate = 0.05
    total = amount

    if country == "US":
        if tier == "enterprise":
            tax_rate = 0.02
        elif tier == "pro":
            tax_rate = 0.04
        else:
            tax_rate = 0.08
    elif country == "EU":
        if tier == "enterprise":
            tax_rate = 0.15
        elif tier == "pro":
            tax_rate = 0.18
        else:
            tax_rate = 0.20
    elif country == "CA":
        if is_partner:
            tax_rate = 0.03
        else:
            tax_rate = 0.12
    else:
        if amount > 1000:
            tax_rate = 0.10
        else:
            tax_rate = 0.05

    if discount_code == "SUMMER50":
        if amount > 200:
            total = total * 0.5
    elif discount_code == "VIP10":
        if is_partner or tier == "enterprise":
            total = total * 0.9

    final_amount = total * (1.0 + tax_rate)
    return round(final_amount, 2)


def duplicate_block_demo(user_role: str):
    """Planted: Duplicate logic block identical to auth.py."""
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
