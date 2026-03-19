"""Local report generation from Fakturoid data."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def monthly_report(invoices: list[dict[str, Any]], year: int, month: int) -> str:
    filtered = []
    for inv in invoices:
        issued = inv.get("issued_on", "")
        if issued and issued.startswith(f"{year}-{month:02d}"):
            filtered.append(inv)

    total = sum(float(inv.get("total", 0)) for inv in filtered)
    paid = [i for i in filtered if i.get("status") == "paid"]
    unpaid = [i for i in filtered if i.get("status") != "paid"]

    lines = [
        f"# Monthly Report — {year}-{month:02d}",
        "",
        f"Invoices issued: {len(filtered)}",
        f"Total amount: {total:,.0f} CZK",
        f"Paid: {len(paid)}",
        f"Unpaid: {len(unpaid)}",
        "",
    ]

    if filtered:
        lines.append("| Number | Client | Amount | Status |")
        lines.append("|--------|--------|--------|--------|")
        for inv in filtered:
            lines.append(
                f"| {inv.get('number', '?')} | {inv.get('client_name', '?')} "
                f"| {inv.get('total', '?')} {inv.get('currency', 'CZK')} | {inv.get('status', '?')} |"
            )

    return "\n".join(lines)


def yearly_report(invoices: list[dict[str, Any]], year: int) -> str:
    by_month: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for inv in invoices:
        issued = inv.get("issued_on", "")
        if issued and issued.startswith(str(year)):
            month = int(issued.split("-")[1])
            by_month[month].append(inv)

    lines = [f"# Yearly Report — {year}", ""]
    grand_total = 0.0

    lines.append("| Month | Invoices | Revenue | Paid |")
    lines.append("|-------|----------|---------|------|")
    for m in range(1, 13):
        month_invs = by_month.get(m, [])
        total = sum(float(i.get("total", 0)) for i in month_invs)
        paid = sum(1 for i in month_invs if i.get("status") == "paid")
        grand_total += total
        if month_invs:
            lines.append(f"| {m:02d} | {len(month_invs)} | {total:,.0f} CZK | {paid}/{len(month_invs)} |")

    lines.append(f"\n**Total revenue: {grand_total:,.0f} CZK**")
    return "\n".join(lines)
