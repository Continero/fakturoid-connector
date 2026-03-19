"""Discord webhook notifications for invoice due dates."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import requests


def _get_amount(item: dict[str, Any]) -> float:
    """Get the relevant amount from an item (remaining or total)."""
    val = item.get("remaining_amount") or item.get("total", 0)
    return float(val) if val else 0.0


def _categorize_by_due(
    items: list[dict[str, Any]], today_date: date, name_field: str
) -> tuple[list[tuple[str, float, str]], list[tuple[str, float, str]], list[tuple[str, float, str]]]:
    """Categorize items into overdue, due today, due soon. Returns (entry_text, amount, currency)."""
    overdue = []
    due_today = []
    due_soon = []

    for item in items:
        if item.get("status") in ("paid", "cancelled"):
            continue
        due_on = item.get("due_on")
        if not due_on:
            continue
        due_date = datetime.strptime(due_on, "%Y-%m-%d").date()
        diff = (due_date - today_date).days

        name = item.get(name_field, item.get("number", "?"))
        amount = _get_amount(item)
        currency = item.get("currency", "CZK")
        entry = f"  \u2022 {item.get('number', '?')} | {name} | {amount:,.0f} {currency}"

        if diff < 0:
            overdue.append((f"{entry} | {abs(diff)} dn\u00ed po splatnosti", amount, currency))
        elif diff == 0:
            due_today.append((entry, amount, currency))
        elif diff <= 3:
            label = "z\u00edtra" if diff == 1 else f"za {diff} dny"
            due_soon.append((f"{entry} | {label}", amount, currency))

    return overdue, due_today, due_soon


def _format_section(
    overdue: list[tuple[str, float, str]],
    due_today: list[tuple[str, float, str]],
    due_soon: list[tuple[str, float, str]],
) -> list[str]:
    """Format overdue/today/soon into message lines."""
    lines = []
    if overdue:
        lines.append(f"\U0001f534 Po splatnosti ({len(overdue)}):")
        lines.extend(entry for entry, _, _ in overdue)
        lines.append("")
    if due_today:
        lines.append(f"\U0001f7e1 Splatn\u00e9 dnes ({len(due_today)}):")
        lines.extend(entry for entry, _, _ in due_today)
        lines.append("")
    if due_soon:
        lines.append(f"\U0001f7e2 Splatn\u00e9 do 3 dn\u016f ({len(due_soon)}):")
        lines.extend(entry for entry, _, _ in due_soon)
        lines.append("")
    return lines


def _sum_by_currency(items: list[tuple[str, float, str]]) -> str:
    """Sum amounts grouped by currency, return formatted string."""
    totals: dict[str, float] = {}
    for _, amount, currency in items:
        totals[currency] = totals.get(currency, 0) + amount
    parts = [f"{total:,.0f} {cur}" for cur, total in sorted(totals.items())]
    return " + ".join(parts) if parts else "0 CZK"


def build_due_message(
    invoices: list[dict[str, Any]],
    expenses: list[dict[str, Any]] | None = None,
    *,
    today: str | None = None,
) -> str:
    """Build Discord message with separate sections for invoices and expenses."""
    today_date = datetime.strptime(today, "%Y-%m-%d").date() if today else date.today()

    lines = []

    # --- Invoices: what clients owe you ---
    inv_overdue, inv_today, inv_soon = _categorize_by_due(invoices, today_date, "client_name")
    inv_lines = _format_section(inv_overdue, inv_today, inv_soon)

    if inv_lines:
        all_shown = inv_overdue + inv_today + inv_soon
        lines.append("**\U0001f4e4 FAKTURY \u2014 co m\u00e1te dostat:**")
        lines.append("")
        lines.extend(inv_lines)
        lines.append(f"\U0001f4b0 Celkem k inkasu: {_sum_by_currency(all_shown)}")
        lines.append("")

    # --- Expenses: split into manual and inkaso ---
    if expenses:
        manual = [e for e in expenses if "inkaso" not in (t.lower() for t in e.get("tags", []))]
        inkaso = [e for e in expenses if "inkaso" in (t.lower() for t in e.get("tags", []))]

        # Manual expenses: what you need to pay yourself
        exp_overdue, exp_today, exp_soon = _categorize_by_due(manual, today_date, "supplier_name")
        exp_lines = _format_section(exp_overdue, exp_today, exp_soon)

        if exp_lines:
            all_shown = exp_overdue + exp_today + exp_soon
            lines.append("---")
            lines.append("")
            lines.append("**\U0001f4e5 N\u00c1KLADY \u2014 co mus\u00edte zaplatit:**")
            lines.append("")
            lines.extend(exp_lines)
            lines.append(f"\U0001f4b8 Celkem k \u00fahrad\u011b: {_sum_by_currency(all_shown)}")
            lines.append("")

        # Inkaso expenses: auto-deducted
        ink_overdue, ink_today, ink_soon = _categorize_by_due(inkaso, today_date, "supplier_name")
        ink_lines = _format_section(ink_overdue, ink_today, ink_soon)

        if ink_lines:
            all_shown = ink_overdue + ink_today + ink_soon
            lines.append("---")
            lines.append("")
            lines.append("**\U0001f3e6 INKASO \u2014 strhne se samo:**")
            lines.append("")
            lines.extend(ink_lines)
            lines.append(f"\U0001f4b3 Celkem inkaso: {_sum_by_currency(all_shown)}")

    if not lines:
        return "\u2705 \u017d\u00e1dn\u00e9 faktury ani n\u00e1klady k \u0159e\u0161en\u00ed."

    return "\n".join(lines)


def send_discord(webhook_url: str, message: str) -> None:
    """Send a message to Discord via webhook."""
    resp = requests.post(webhook_url, json={"content": message})
    resp.raise_for_status()
