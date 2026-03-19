"""Fakturoid CLI commands."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import click
from dotenv import load_dotenv

from fakturoid_connector.client import FakturoidClient

load_dotenv()


def _get_client() -> FakturoidClient:
    return FakturoidClient(
        client_id=os.environ["FAKTUROID_CLIENT_ID"],
        client_secret=os.environ["FAKTUROID_CLIENT_SECRET"],
        slug=os.environ["FAKTUROID_SLUG"],
    )


@click.group()
def cli():
    """Fakturoid.cz connector — invoices, contacts, reports."""
    pass


@cli.command()
@click.argument("query")
def search(query: str):
    """Search invoices by text."""
    client = _get_client()
    invoices = client.search_invoices(query)
    for inv in invoices:
        status = inv.get("status", "?")
        click.echo(f"  {inv['number']}  {inv.get('client_name', '?')}  "
                    f"{inv.get('total', '?')} {inv.get('currency', 'CZK')}  [{status}]")
    if not invoices:
        click.echo("No invoices found.")


@cli.command()
@click.option("--overdue", is_flag=True, help="Only overdue invoices")
@click.option("--unpaid", is_flag=True, help="Only unpaid invoices")
@click.option("--status", type=str, default=None, help="Filter by status")
def invoices(overdue: bool, unpaid: bool, status: str | None):
    """List invoices."""
    client = _get_client()
    if overdue:
        status = "overdue"
    elif unpaid:
        status = "open"
    results = client.list_invoices(status=status)
    for inv in results:
        st = inv.get("status", "?")
        click.echo(f"  {inv['number']}  {inv.get('client_name', '?')}  "
                    f"{inv.get('total', '?')} {inv.get('currency', 'CZK')}  [{st}]  "
                    f"due: {inv.get('due_on', '?')}")
    click.echo(f"\nTotal: {len(results)} invoices")


@cli.command()
@click.argument("invoice_id", type=int)
def invoice(invoice_id: int):
    """Show invoice detail."""
    client = _get_client()
    inv = client.get_invoice(invoice_id)
    click.echo(json.dumps(inv, indent=2, ensure_ascii=False))


@cli.command()
def contacts():
    """List all contacts."""
    client = _get_client()
    subjects = client.list_subjects()
    for s in subjects:
        click.echo(f"  [{s['id']}] {s['name']}  {s.get('email', '')}")
    click.echo(f"\nTotal: {len(subjects)} contacts")


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["json", "csv"]), default="json")
@click.option("-o", "--output", type=click.Path(), default="output")
def export(fmt: str, output: str):
    """Export all invoices to JSON or CSV."""
    client = _get_client()
    all_invoices = client.list_invoices()
    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)

    if fmt == "json":
        path = out_dir / "invoices.json"
        path.write_text(json.dumps(all_invoices, indent=2, ensure_ascii=False))
        click.echo(f"Exported {len(all_invoices)} invoices to {path}")
    elif fmt == "csv":
        import csv
        path = out_dir / "invoices.csv"
        if not all_invoices:
            click.echo("No invoices to export.")
            return
        keys = ["number", "client_name", "issued_on", "due_on", "total", "currency", "status"]
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(all_invoices)
        click.echo(f"Exported {len(all_invoices)} invoices to {path}")


@cli.command("export-pdf")
@click.argument("invoice_id", type=int)
@click.option("-o", "--output", type=click.Path(), default="output")
def export_pdf(invoice_id: int, output: str):
    """Download invoice PDF."""
    client = _get_client()
    inv = client.get_invoice(invoice_id)
    pdf = client.download_invoice_pdf(invoice_id)
    if pdf is None:
        click.echo("PDF not ready yet, try again later.")
        return
    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{inv.get('number', invoice_id)}.pdf"
    path = out_dir / filename
    path.write_bytes(pdf)
    click.echo(f"Downloaded {path}")


@cli.command()
def summary():
    """Show account summary."""
    client = _get_client()
    account = client.get_account()
    invoices_all = client.list_invoices()
    overdue = [i for i in invoices_all if i.get("status") == "overdue"]
    unpaid = [i for i in invoices_all if i.get("status") in ("open", "sent", "overdue")]

    click.echo(f"Account: {account.get('name', '?')}")
    click.echo(f"Plan: {account.get('plan', '?')}")
    click.echo(f"Total invoices: {len(invoices_all)}")
    click.echo(f"Unpaid: {len(unpaid)}")
    click.echo(f"Overdue: {len(overdue)}")
    if unpaid:
        total_unpaid = sum(float(i.get("remaining_amount", 0)) for i in unpaid)
        click.echo(f"Total unpaid: {total_unpaid:,.0f} CZK")


@cli.group()
def report():
    """Generate reports."""
    pass


@report.command()
@click.option("--year", type=int, default=None)
@click.option("--month", type=int, default=None)
def monthly(year: int | None, month: int | None):
    """Monthly invoice report."""
    from fakturoid_connector.reports import monthly_report
    now = datetime.now()
    year = year or now.year
    month = month or now.month
    client = _get_client()
    invoices_data = client.list_invoices()
    click.echo(monthly_report(invoices_data, year, month))


@report.command()
@click.option("--year", type=int, default=None)
def yearly(year: int | None):
    """Yearly invoice report."""
    from fakturoid_connector.reports import yearly_report
    now = datetime.now()
    year = year or now.year
    client = _get_client()
    invoices_data = client.list_invoices()
    click.echo(yearly_report(invoices_data, year))


@cli.command("check-due")
def check_due():
    """Check due invoices and expenses, send Discord notification."""
    from fakturoid_connector.notifications import build_due_message, send_discord
    client = _get_client()
    invoices_data = client.list_invoices()
    expenses_data = client.list_expenses()
    message = build_due_message(invoices_data, expenses_data)
    click.echo(message)

    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if webhook_url:
        send_discord(webhook_url, message)
        click.echo("\nDiscord notification sent.")
    else:
        click.echo("\nDISCORD_WEBHOOK_URL not set, skipping notification.")


@cli.command()
@click.option("--due-date", type=str, default=None,
              help="Include expenses due on or before this date (YYYY-MM-DD). Default: today.")
@click.option("--status", type=str, default="open",
              help="Expense status filter (default: open)")
@click.option("-o", "--output", type=click.Path(), default="output",
              help="Output directory for the ABO file")
def abo(due_date: str | None, status: str, output: str):
    """Generate ABO payment order file from unpaid expenses."""
    from fakturoid_connector.abo import generate_abo

    sender_account = os.environ.get("FAKTUROID_SENDER_ACCOUNT")
    if not sender_account:
        click.echo("Error: FAKTUROID_SENDER_ACCOUNT not set in .env")
        click.echo("Format: prefix-number/bank_code (e.g. 000000-2301502986/2010)")
        raise SystemExit(1)

    sender_name = os.environ.get("FAKTUROID_SENDER_NAME", "")
    sender_ico = os.environ.get("FAKTUROID_SENDER_ICO", "")

    client = _get_client()
    expenses_data = client.list_expenses(status=status)

    # Filter by due date
    if due_date:
        cutoff = datetime.strptime(due_date, "%Y-%m-%d").date()
    else:
        cutoff = datetime.now().date()

    filtered = []
    for exp in expenses_data:
        exp_due = exp.get("due_on")
        if not exp_due:
            continue
        if datetime.strptime(exp_due, "%Y-%m-%d").date() <= cutoff:
            filtered.append(exp)

    if not filtered:
        click.echo("No expenses matching criteria.")
        return

    # Show what will be included
    click.echo(f"Generating ABO for {len(filtered)} expenses (due <= {cutoff}):\n")
    for exp in filtered:
        click.echo(f"  {exp.get('number', '?')} | {exp.get('supplier_name', '?')} | "
                    f"{exp.get('total', '?')} {exp.get('currency', 'CZK')} | "
                    f"due: {exp.get('due_on', '?')}")

    total = sum(float(e.get("total", 0)) for e in filtered)
    click.echo(f"\nTotal: {total:,.2f} CZK")

    content = generate_abo(
        filtered,
        sender_account=sender_account,
        sender_name=sender_name,
        sender_ico=sender_ico,
        payment_date=cutoff,
    )

    if not content:
        click.echo("\nNo valid expenses (missing bank account?).")
        return

    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"expenses_{cutoff.strftime('%Y-%m-%d')}.abo"
    path = out_dir / filename
    path.write_text(content, encoding="ascii", errors="replace")
    click.echo(f"\nABO file saved: {path}")
