"""ABO file generator for Czech bank payment orders.

ABO is a fixed-width text format used by Czech banks for batch payment imports.
This module generates ABO files from Fakturoid expense data.

Format reference (matching Fakturoid's output):
  Line 1 (UHL): Header with date, sender name, account ID
  Line 2: Batch header with sender bank code
  Line 3: Group record with sender account, total amount, date
  Lines 4+: Payment detail lines (one per expense)
  Footer: "3 +" and "5 +"
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


def _parse_account(account_str: str) -> tuple[str, str, str]:
    """Parse Czech bank account 'prefix-number/bank_code' into (prefix, number, bank_code).

    Handles formats: '123456-7890123456/0100', '7890123456/0100', '7890123456/ 0100'
    """
    account_str = account_str.strip()
    if "/" not in account_str:
        raise ValueError(f"Invalid account format (missing /): {account_str}")
    account_part, bank_code = account_str.rsplit("/", 1)
    bank_code = bank_code.strip()
    if "-" in account_part:
        prefix, number = account_part.split("-", 1)
    else:
        prefix = "0"
        number = account_part
    return prefix.strip(), number.strip(), bank_code.strip()


def generate_abo(
    expenses: list[dict[str, Any]],
    *,
    sender_account: str,
    sender_name: str = "",
    sender_ico: str = "",
    payment_date: date | None = None,
) -> str:
    """Generate ABO file content from a list of Fakturoid expenses.

    Args:
        expenses: Expense dicts from Fakturoid API. Required fields:
            bank_account, total. Optional: variable_symbol, constant_symbol.
        sender_account: Sender bank account ('prefix-number/bank_code' or 'number/bank_code')
        sender_name: Company name for AV field
        sender_ico: Company ICO for AV field
        payment_date: Date for the payment order (default: today)

    Returns:
        ABO file content as string, or empty string if no valid expenses.
    """
    if not expenses:
        return ""

    payment_date = payment_date or date.today()
    sender_prefix, sender_number, sender_bank = _parse_account(sender_account)
    date_str = payment_date.strftime("%d%m%y")

    # Build AV (avizo) message
    av_parts = []
    if sender_name:
        av_parts.append(sender_name)
    if sender_ico:
        av_parts.append(f"IC {sender_ico}")
    av_msg = "AV:" + ", ".join(av_parts) if av_parts else ""

    # Filter valid expenses (must have bank_account and positive amount)
    valid_expenses = []
    for exp in expenses:
        bank_account = exp.get("bank_account", "")
        if not bank_account or "/" not in bank_account:
            continue
        amount = float(exp.get("total", 0))
        if amount <= 0:
            continue
        valid_expenses.append(exp)

    if not valid_expenses:
        return ""

    # Calculate total in hellers
    total_hellers = sum(round(float(e.get("total", 0)) * 100) for e in valid_expenses)

    lines = []

    # Line 1: UHL header
    # UHL1 + DDMMYY + name(20) + account_id(16) + zeros(10)
    name_padded = f"{sender_name.upper()[:20]:<20}"
    account_id = f"{int(sender_prefix):06d}{int(sender_number):010d}"
    lines.append(f"UHL1{date_str}{name_padded}{account_id}0000000000")

    # Line 2: Batch header
    # 1 + bank_code(4) + prefix(6) + bank_code(4)
    lines.append(
        f"1 {int(sender_bank):04d} "
        f"{int(sender_prefix):06d} "
        f"{int(sender_bank):04d}"
    )

    # Line 3: Group record (type 2) — sender account + total + date
    sender_fmt = f"{int(sender_prefix):06d}-{int(sender_number):010d}"
    lines.append(f"2 {sender_fmt} {total_hellers:014d} {date_str}")

    # Lines 4+: Payment details
    for exp in valid_expenses:
        rcv_prefix, rcv_number, rcv_bank = _parse_account(exp["bank_account"])
        amount_hellers = round(float(exp.get("total", 0)) * 100)
        vs = str(exp.get("variable_symbol", "0") or "0").strip()
        ks = str(exp.get("constant_symbol", "0") or "0").strip()

        rcv_fmt = f"{int(rcv_prefix):06d}-{int(rcv_number):010d}"
        amount_fmt = f"{amount_hellers:012d}"
        vs_fmt = f"{int(vs):010d}"
        bank_ks_fmt = f"{int(rcv_bank):04d}{int(ks):06d}"

        line = (
            f"{rcv_fmt} "
            f"{amount_fmt} "
            f"{vs_fmt} "
            f"{bank_ks_fmt} "
            f"0000000000 "
            f"{av_msg}"
        )
        lines.append(line)

    # Footer
    lines.append("3 +")
    lines.append("5 +")

    return "\r\n".join(lines) + "\r\n"
