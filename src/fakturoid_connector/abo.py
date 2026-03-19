"""ABO file generator for Czech bank payment orders.

ABO is a fixed-width text format used by Czech banks for batch payment imports.
This module generates ABO files from Fakturoid expense data.

Format reference: Česká spořitelna "Technical Description of the ABO Format
Structure for Programmers" (3-2267a).

Record structure:
  UHL1          - File header (date, client name, client number, intervals, codes)
  1 ...         - Accounting file header (type=1501 for payments, file number, bank code)
  2 ...         - Group header (payer account, total amount, due date)
  <items>       - Payment items (credit account, amount, VS, KS+bank, SS, message)
  3 +           - End of group
  5 +           - End of accounting file
"""

from __future__ import annotations

from datetime import date
from typing import Any


def _parse_account(account_str: str) -> tuple[str, str, str]:
    """Parse Czech bank account into (prefix, number, bank_code).

    Accepts: '000131-2733070267/0100', '2733070267/0100', '2733070267/ 0100'
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
            bank_account, total. Optional: variable_symbol.
        sender_account: Sender bank account ('prefix-number/bank_code' or 'number/bank_code')
        sender_name: Company name for AV field and UHL1 header
        sender_ico: Company ICO for AV field
        payment_date: Date for the payment order (default: today)

    Returns:
        ABO file content as string (CR LF line endings), or empty string if no valid expenses.
    """
    if not expenses:
        return ""

    payment_date = payment_date or date.today()
    sender_prefix, sender_number, sender_bank = _parse_account(sender_account)
    date_str = payment_date.strftime("%d%m%y")

    # Build AV (avizo) message for recipient
    av_parts = []
    if sender_name:
        av_parts.append(sender_name)
    if sender_ico:
        av_parts.append(f"IC {sender_ico}")
    av_msg = "AV:" + ", ".join(av_parts) if av_parts else ""

    # Filter valid expenses (must have bank_account with / and positive amount)
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

    # ── UHL1 Record ──────────────────────────────────────────────
    # Seq 1: Message type        F  4   "UHL1"
    # Seq 2: Code date           F  6   ddmmyy
    # Seq 3: Client name         F 20   alphanumeric, padded with spaces
    # Seq 4: Client number       F 10   account number (mandatory part, no prefix)
    # Seq 5: Interval start      F  3   NNN
    # Seq 6: Interval end        F  3   NNN
    # Seq 7: Code fixed part     F  6   NNNNNN
    # Seq 8: Code secret part    F  6   NNNNNN
    name_padded = f"{sender_name.upper()[:20]:<20}"
    client_number = f"{int(sender_number):010d}"
    uhl = f"UHL1{date_str}{name_padded}{client_number}001001000000000000"
    lines.append(uhl)

    # ── Accounting File Header ───────────────────────────────────
    # Seq 1: Message type        F  1   "1"
    # Seq 2: Separator           F  1   space
    # Seq 3: Type of data        F  4   "1501" (payment orders)
    # Seq 4: Separator           F  1   space
    # Seq 5: File number         F  6   sssppp
    # Seq 6: Separator           F  1   space
    # Seq 7: Bank code           F  4   sender bank code
    lines.append(f"1 1501 001000 {int(sender_bank):04d}")

    # ── Group Header ─────────────────────────────────────────────
    # Seq 1: Message type        F  1   "2"
    # Seq 2: Separator           F  1   space
    # Seq 3: Payer account       V 2-17 NNNNNN-NNNNNNNNNN
    # Seq 4: Separator           F  1   space
    # Seq 5: Total amount        V 1-14 in hellers
    # Seq 6: Separator           F  1   space
    # Seq 7: Due date            F  6   ddmmyy
    sender_fmt = f"{int(sender_prefix):06d}-{int(sender_number):010d}"
    lines.append(f"2 {sender_fmt} {total_hellers:014d} {date_str}")

    # ── Payment Items (batch — no debit account, starts with credit) ──
    # Seq 3:  Account credit     V 2-17 NNNNNN-NNNNNNNNNN
    # Seq 5:  Amount             V 1-12 in hellers
    # Seq 7:  Variable symbol    V 1-10
    # Seq 9:  Constant symbol    V 8-10 (bank code pos 5-8 from right, KS pos 1-4 from right)
    # Seq 11: Specific symbol    V 0-10
    # Seq 13: Message            V 0-35
    for exp in valid_expenses:
        rcv_prefix, rcv_number, rcv_bank = _parse_account(exp["bank_account"])
        amount_hellers = round(float(exp.get("total", 0)) * 100)
        vs = str(exp.get("variable_symbol", "0") or "0").strip()

        rcv_fmt = f"{int(rcv_prefix):06d}-{int(rcv_number):010d}"
        amount_fmt = f"{amount_hellers:012d}"
        vs_fmt = f"{int(vs):010d}"

        # KS field (10 chars): positions from right:
        #   1-4: constant symbol (default 0000)
        #   5-8: recipient bank code
        #   9-10: payment type prefix (05 for standard payment)
        ks_field = f"05{int(rcv_bank):04d}0000{'00'}"
        # That gives 12 chars — wrong. The field is 10 chars max.
        # Correct: "05" + bank(4) + "0000" = 10 chars
        ks_field = f"05{int(rcv_bank):04d}0000"

        line = (
            f"{rcv_fmt} "
            f"{amount_fmt} "
            f"{vs_fmt} "
            f"{ks_field} "
            f"0000000000 "
            f"{av_msg}"
        )
        lines.append(line)

    # ── End of Group ─────────────────────────────────────────────
    lines.append("3 +")

    # ── End of Accounting File ───────────────────────────────────
    lines.append("5 +")

    return "\r\n".join(lines) + "\r\n"
