"""MCP Server for Fakturoid — exposes tools for Claude Code."""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from fakturoid_connector.client import FakturoidClient

load_dotenv()

mcp = FastMCP("fakturoid")

_client: FakturoidClient | None = None


def _get_client() -> FakturoidClient:
    global _client
    if _client is None:
        _client = FakturoidClient(
            client_id=os.environ["FAKTUROID_CLIENT_ID"],
            client_secret=os.environ["FAKTUROID_CLIENT_SECRET"],
            slug=os.environ["FAKTUROID_SLUG"],
        )
    return _client


@mcp.tool()
def search_invoices(query: str) -> str:
    """Search invoices by text (client name, number, description)."""
    client = _get_client()
    results = client.search_invoices(query)
    return json.dumps(results[:20], indent=2, ensure_ascii=False)


@mcp.tool()
def get_invoice(invoice_id: int) -> str:
    """Get full detail of a specific invoice by ID."""
    client = _get_client()
    return json.dumps(client.get_invoice(invoice_id), indent=2, ensure_ascii=False)


@mcp.tool()
def list_overdue_invoices() -> str:
    """List all overdue invoices."""
    client = _get_client()
    results = client.list_invoices(status="overdue")
    return json.dumps(results, indent=2, ensure_ascii=False)


@mcp.tool()
def list_unpaid_invoices() -> str:
    """List all unpaid/open invoices."""
    client = _get_client()
    results = client.list_invoices(status="open")
    return json.dumps(results, indent=2, ensure_ascii=False)


@mcp.tool()
def create_invoice(
    subject_id: int,
    lines: list[dict],
    due_days: int = 14,
    currency: str = "CZK",
    note: str = "",
) -> str:
    """Create a new invoice.

    Args:
        subject_id: ID of the client/subject
        lines: Invoice line items, each with 'name', 'unit_price', 'quantity'
        due_days: Payment due in days (default 14)
        currency: Currency code (default CZK)
        note: Optional invoice note
    """
    client = _get_client()
    data: dict = {
        "subject_id": subject_id,
        "currency": currency,
        "due": due_days,
        "lines": lines,
    }
    if note:
        data["note"] = note
    result = client.create_invoice(data)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def list_contacts(query: str = "") -> str:
    """List or search contacts/clients. Pass query to search, empty for all."""
    client = _get_client()
    if query:
        results = client.search_subjects(query)
    else:
        results = client.list_subjects()
    summary = [
        {"id": s["id"], "name": s["name"], "email": s.get("email", ""),
         "registration_no": s.get("registration_no", "")}
        for s in results[:50]
    ]
    return json.dumps(summary, indent=2, ensure_ascii=False)


@mcp.tool()
def get_contact(subject_id: int) -> str:
    """Get full detail of a contact/client by ID."""
    client = _get_client()
    return json.dumps(client.get_subject(subject_id), indent=2, ensure_ascii=False)


@mcp.tool()
def get_account_summary() -> str:
    """Get account overview: company info, invoice stats, overdue amounts."""
    client = _get_client()
    account = client.get_account()
    all_invoices = client.list_invoices()
    overdue = [i for i in all_invoices if i.get("status") == "overdue"]
    unpaid = [i for i in all_invoices if i.get("status") in ("open", "sent", "overdue")]

    return json.dumps({
        "account_name": account.get("name"),
        "plan": account.get("plan"),
        "total_invoices": len(all_invoices),
        "unpaid_count": len(unpaid),
        "overdue_count": len(overdue),
        "total_unpaid_czk": sum(float(i.get("remaining_amount", 0)) for i in unpaid),
        "total_overdue_czk": sum(float(i.get("remaining_amount", 0)) for i in overdue),
    }, indent=2, ensure_ascii=False)


@mcp.tool()
def download_invoice_pdf(invoice_id: int, output_dir: str = "output") -> str:
    """Download invoice as PDF to local file."""
    client = _get_client()
    inv = client.get_invoice(invoice_id)
    pdf = client.download_invoice_pdf(invoice_id)
    if pdf is None:
        return "PDF not ready yet."
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    filename = f"{inv.get('number', invoice_id)}.pdf"
    filepath = path / filename
    filepath.write_bytes(pdf)
    return f"Downloaded to {filepath}"


@mcp.tool()
def list_expenses(status: str = "") -> str:
    """List expenses, optionally filtered by status (open, overdue, paid)."""
    client = _get_client()
    results = client.list_expenses(status=status or None)
    return json.dumps(results[:30], indent=2, ensure_ascii=False)


@mcp.tool()
def generate_abo_file(due_date: str = "", output_dir: str = "output") -> str:
    """Generate ABO payment order file from unpaid expenses.

    Args:
        due_date: Include expenses due on or before this date (YYYY-MM-DD). Default: today.
        output_dir: Directory to save the ABO file (default: output/)

    Requires FAKTUROID_SENDER_ACCOUNT, FAKTUROID_SENDER_NAME, FAKTUROID_SENDER_ICO in .env.
    """
    from datetime import date as date_cls, datetime as dt_cls
    from fakturoid_connector.abo import generate_abo

    sender_account = os.environ.get("FAKTUROID_SENDER_ACCOUNT")
    if not sender_account:
        return "Error: FAKTUROID_SENDER_ACCOUNT not set in .env (format: prefix-number/bank_code)"

    cutoff = dt_cls.strptime(due_date, "%Y-%m-%d").date() if due_date else date_cls.today()

    client = _get_client()
    expenses = client.list_expenses(status="open")

    filtered = []
    for exp in expenses:
        exp_due = exp.get("due_on")
        if exp_due and dt_cls.strptime(exp_due, "%Y-%m-%d").date() <= cutoff:
            filtered.append(exp)

    if not filtered:
        return f"No unpaid expenses due on or before {cutoff}."

    content = generate_abo(
        filtered,
        sender_account=sender_account,
        sender_name=os.environ.get("FAKTUROID_SENDER_NAME", ""),
        sender_ico=os.environ.get("FAKTUROID_SENDER_ICO", ""),
        payment_date=cutoff,
    )

    if not content:
        return "No valid expenses (missing bank account data?)."

    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    filename = f"expenses_{cutoff.strftime('%Y-%m-%d')}.abo"
    filepath = path / filename
    filepath.write_text(content, encoding="ascii", errors="replace")

    summary = [f"ABO file saved: {filepath}", f"Expenses: {len(filtered)}", f"Due date: {cutoff}", ""]
    for exp in filtered:
        summary.append(f"  {exp.get('number', '?')} | {exp.get('supplier_name', '?')} | "
                       f"{exp.get('total', '?')} {exp.get('currency', 'CZK')}")
    total = sum(float(e.get("total", 0)) for e in filtered)
    summary.append(f"\nTotal: {total:,.2f} CZK")

    return "\n".join(summary)
