# Fakturoid Connector Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** AI-powered Fakturoid.cz connector — MCP Server for natural language interaction, CLI for automation, Discord webhook for due date notifications.

**Architecture:** Python package with three interfaces: (1) `client.py` wraps Fakturoid API v3 with OAuth 2 Client Credentials, (2) `cli.py` provides Click commands for search, export, reports, due checks, (3) `mcp_server.py` exposes tools for Claude Code. Discord notifications via webhook. Skill file teaches Claude when to use CLI vs MCP.

**Tech Stack:** Python 3.10+, requests, click, python-dotenv, mcp (Python SDK)

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/fakturoid_connector/__init__.py`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `README.md`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "fakturoid-connector"
version = "0.1.0"
description = "AI-powered Fakturoid.cz connector — MCP Server + CLI + Discord notifications"
requires-python = ">=3.10"
dependencies = [
    "requests>=2.31",
    "click>=8.1",
    "python-dotenv>=1.0",
    "mcp[cli]>=1.0",
]

[project.scripts]
fakturoid = "fakturoid_connector.cli:cli"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]
```

**Step 2: Create __init__.py**

```python
"""Fakturoid.cz connector — MCP Server + CLI + Discord notifications."""
```

**Step 3: Create .env.example**

```env
FAKTUROID_CLIENT_ID=your_client_id
FAKTUROID_CLIENT_SECRET=your_client_secret
FAKTUROID_SLUG=your_account_slug
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

**Step 4: Create .gitignore**

```
__pycache__/
*.egg-info/
dist/
build/
.env
.venv/
output/
```

**Step 5: Create README.md**

Brief readme with project description, setup instructions (.env, pip install -e .), usage examples for CLI and MCP.

**Step 6: Initialize git and connect to GitHub**

```bash
cd /Users/fogl/Documents/PROJECTS/fakturoid-connector
git init
git remote add origin git@github.com:Continero/fakturoid-connector.git
git add pyproject.toml src/ .env.example .gitignore README.md
git commit -m "feat: project scaffolding"
git branch -M main
git push -u origin main
```

---

### Task 2: OAuth 2 Client — Authentication

**Files:**
- Create: `src/fakturoid_connector/client.py`
- Create: `tests/test_client.py`

**Step 1: Write the failing test**

```python
"""Tests for FakturoidClient."""

import json
from unittest.mock import patch, MagicMock
import pytest
from fakturoid_connector.client import FakturoidClient


def _mock_token_response():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "access_token": "test_token_123",
        "token_type": "Bearer",
        "expires_in": 7200,
    }
    return resp


@patch("fakturoid_connector.client.requests.Session")
def test_authenticate_sets_bearer_token(mock_session_cls):
    session = MagicMock()
    mock_session_cls.return_value = session
    session.post.return_value = _mock_token_response()

    client = FakturoidClient(
        client_id="test_id",
        client_secret="test_secret",
        slug="testcorp",
    )

    session.post.assert_called_once()
    call_args = session.post.call_args
    assert "oauth/token" in call_args[0][0]
```

**Step 2: Run test to verify it fails**

Run: `rtk python -m pytest tests/test_client.py -v`
Expected: FAIL — module not found

**Step 3: Write minimal implementation**

```python
"""Fakturoid API v3 client with OAuth 2 Client Credentials."""

from __future__ import annotations

import base64
import time
from typing import Any

import requests

API_BASE = "https://app.fakturoid.cz/api/v3"
USER_AGENT = "FakturoidConnector (github.com/Continero/fakturoid-connector)"


class FakturoidClient:
    """Client for the Fakturoid REST API v3."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        slug: str,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._slug = slug
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        })
        self._token: str | None = None
        self._token_expires_at: float = 0
        self._authenticate()

    def _authenticate(self) -> None:
        """Obtain access token via Client Credentials flow."""
        credentials = base64.b64encode(
            f"{self._client_id}:{self._client_secret}".encode()
        ).decode()
        resp = self._session.post(
            f"{API_BASE}/oauth/token",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/json",
            },
            json={"grant_type": "client_credentials"},
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        self._token_expires_at = time.time() + data.get("expires_in", 7200) - 60
        self._session.headers.update({"Authorization": f"Bearer {self._token}"})

    def _ensure_token(self) -> None:
        """Re-authenticate if token is expired."""
        if time.time() >= self._token_expires_at:
            self._authenticate()

    @property
    def _base(self) -> str:
        return f"{API_BASE}/accounts/{self._slug}"

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        self._ensure_token()
        resp = self._session.get(f"{self._base}{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    def _get_all(self, path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Auto-paginate a GET endpoint (40 items per page)."""
        self._ensure_token()
        params = dict(params or {})
        results: list[dict[str, Any]] = []
        page = 1
        while True:
            params["page"] = page
            resp = self._session.get(f"{self._base}{path}", params=params)
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            results.extend(data)
            if len(data) < 40:
                break
            page += 1
        return results

    def _post(self, path: str, json_data: dict[str, Any] | None = None) -> Any:
        self._ensure_token()
        resp = self._session.post(f"{self._base}{path}", json=json_data)
        resp.raise_for_status()
        return resp.json() if resp.content else None

    def _patch(self, path: str, json_data: dict[str, Any]) -> Any:
        self._ensure_token()
        resp = self._session.patch(f"{self._base}{path}", json=json_data)
        resp.raise_for_status()
        return resp.json() if resp.content else None

    def _delete(self, path: str) -> None:
        self._ensure_token()
        resp = self._session.delete(f"{self._base}{path}")
        resp.raise_for_status()
```

**Step 4: Run test to verify it passes**

Run: `rtk python -m pytest tests/test_client.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/fakturoid_connector/client.py tests/test_client.py
git commit -m "feat: OAuth 2 client with auto-refresh"
```

---

### Task 3: Client — Invoice Methods

**Files:**
- Modify: `src/fakturoid_connector/client.py`
- Modify: `tests/test_client.py`

**Step 1: Write failing tests**

```python
@patch("fakturoid_connector.client.requests.Session")
def test_list_invoices(mock_session_cls):
    session = MagicMock()
    mock_session_cls.return_value = session
    session.post.return_value = _mock_token_response()

    invoices_resp = MagicMock()
    invoices_resp.status_code = 200
    invoices_resp.json.return_value = [{"id": 1, "number": "FV-001"}]
    session.get.return_value = invoices_resp

    client = FakturoidClient(client_id="id", client_secret="secret", slug="test")
    result = client.list_invoices()
    assert len(result) == 1
    assert result[0]["number"] == "FV-001"


@patch("fakturoid_connector.client.requests.Session")
def test_search_invoices(mock_session_cls):
    session = MagicMock()
    mock_session_cls.return_value = session
    session.post.return_value = _mock_token_response()

    search_resp = MagicMock()
    search_resp.status_code = 200
    search_resp.json.return_value = [{"id": 1, "number": "FV-001"}]
    session.get.return_value = search_resp

    client = FakturoidClient(client_id="id", client_secret="secret", slug="test")
    result = client.search_invoices("test query")
    assert len(result) == 1
```

**Step 2: Run tests — expect FAIL**

**Step 3: Implement invoice methods**

Add to `FakturoidClient`:

```python
    # ------------------------------------------------------------------
    # Invoices
    # ------------------------------------------------------------------

    def list_invoices(
        self,
        *,
        status: str | None = None,
        subject_id: int | None = None,
        since: str | None = None,
        until: str | None = None,
        number: str | None = None,
        page: int | None = None,
    ) -> list[dict[str, Any]]:
        """List invoices with optional filters. Auto-paginates if page is None."""
        params: dict[str, Any] = {}
        if status:
            params["status"] = status
        if subject_id:
            params["subject_id"] = subject_id
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        if number:
            params["number"] = number
        if page is not None:
            return self._get("/invoices.json", params={**params, "page": page})
        return self._get_all("/invoices.json", params)

    def search_invoices(self, query: str, *, tags: str | None = None) -> list[dict[str, Any]]:
        """Full-text search across invoices."""
        params: dict[str, Any] = {"query": query}
        if tags:
            params["tags"] = tags
        return self._get_all("/invoices/search.json", params)

    def get_invoice(self, invoice_id: int) -> dict[str, Any]:
        """Get single invoice by ID."""
        return self._get(f"/invoices/{invoice_id}.json")

    def create_invoice(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new invoice."""
        return self._post("/invoices.json", data)

    def update_invoice(self, invoice_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing invoice."""
        return self._patch(f"/invoices/{invoice_id}.json", data)

    def download_invoice_pdf(self, invoice_id: int) -> bytes | None:
        """Download invoice as PDF. Returns bytes or None if not ready."""
        self._ensure_token()
        resp = self._session.get(f"{self._base}/invoices/{invoice_id}/download.pdf")
        if resp.status_code == 204:
            return None
        resp.raise_for_status()
        return resp.content

    def fire_invoice(self, invoice_id: int, event: str) -> None:
        """Execute an action on invoice (mark_as_sent, cancel, etc.)."""
        self._ensure_token()
        resp = self._session.post(
            f"{self._base}/invoices/{invoice_id}/fire.json",
            json={"event": event},
        )
        resp.raise_for_status()
```

**Step 4: Run tests — expect PASS**

**Step 5: Commit**

```bash
git add src/fakturoid_connector/client.py tests/test_client.py
git commit -m "feat: invoice API methods"
```

---

### Task 4: Client — Subjects, Expenses, Account

**Files:**
- Modify: `src/fakturoid_connector/client.py`
- Modify: `tests/test_client.py`

**Step 1: Write failing tests for subjects/expenses/account**

**Step 2: Run tests — expect FAIL**

**Step 3: Implement methods**

Add to `FakturoidClient`:

```python
    # ------------------------------------------------------------------
    # Subjects (Contacts)
    # ------------------------------------------------------------------

    def list_subjects(self, *, page: int | None = None) -> list[dict[str, Any]]:
        if page is not None:
            return self._get("/subjects.json", params={"page": page})
        return self._get_all("/subjects.json")

    def search_subjects(self, query: str) -> list[dict[str, Any]]:
        return self._get_all("/subjects/search.json", {"query": query})

    def get_subject(self, subject_id: int) -> dict[str, Any]:
        return self._get(f"/subjects/{subject_id}.json")

    def create_subject(self, data: dict[str, Any]) -> dict[str, Any]:
        return self._post("/subjects.json", data)

    # ------------------------------------------------------------------
    # Expenses
    # ------------------------------------------------------------------

    def list_expenses(
        self, *, status: str | None = None, subject_id: int | None = None, page: int | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if status:
            params["status"] = status
        if subject_id:
            params["subject_id"] = subject_id
        if page is not None:
            return self._get("/expenses.json", params={**params, "page": page})
        return self._get_all("/expenses.json", params)

    def search_expenses(self, query: str) -> list[dict[str, Any]]:
        return self._get_all("/expenses/search.json", {"query": query})

    def get_expense(self, expense_id: int) -> dict[str, Any]:
        return self._get(f"/expenses/{expense_id}.json")

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    def get_account(self) -> dict[str, Any]:
        return self._get("/account.json")
```

**Step 4: Run tests — expect PASS**

**Step 5: Commit**

```bash
git add src/fakturoid_connector/client.py tests/test_client.py
git commit -m "feat: subjects, expenses, account API methods"
```

---

### Task 5: CLI — Core Commands

**Files:**
- Create: `src/fakturoid_connector/cli.py`
- Create: `tests/test_cli.py`

**Step 1: Write failing test**

```python
from click.testing import CliRunner
from fakturoid_connector.cli import cli

def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Fakturoid" in result.output
```

**Step 2: Run test — expect FAIL**

**Step 3: Implement CLI**

```python
"""Fakturoid CLI commands."""

from __future__ import annotations

import json
import os
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


@cli.command()
@click.option("--overdue", is_flag=True, help="Only overdue invoices")
@click.option("--unpaid", is_flag=True, help="Only unpaid invoices")
@click.option("--status", type=str, help="Filter by status")
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
    unpaid = [i for i in invoices_all if i.get("status") in ("open", "sent")]

    click.echo(f"Account: {account.get('name', '?')}")
    click.echo(f"Plan: {account.get('plan', '?')}")
    click.echo(f"Total invoices: {len(invoices_all)}")
    click.echo(f"Unpaid: {len(unpaid)}")
    click.echo(f"Overdue: {len(overdue)}")
    if overdue:
        total_overdue = sum(float(i.get("remaining_amount", 0)) for i in overdue)
        click.echo(f"Total overdue amount: {total_overdue:,.0f} CZK")
```

**Step 4: Run tests — expect PASS**

**Step 5: Commit**

```bash
git add src/fakturoid_connector/cli.py tests/test_cli.py
git commit -m "feat: CLI commands — search, invoices, contacts, export, summary"
```

---

### Task 6: CLI — Reports

**Files:**
- Create: `src/fakturoid_connector/reports.py`
- Modify: `src/fakturoid_connector/cli.py`

**Step 1: Write failing test**

**Step 2: Run test — expect FAIL**

**Step 3: Implement reports**

```python
"""Local report generation from Fakturoid data."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any


def monthly_report(invoices: list[dict[str, Any]], year: int, month: int) -> str:
    """Generate monthly revenue report."""
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
        f"",
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
    """Generate yearly summary grouped by month."""
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
```

Add CLI commands `report monthly` and `report yearly` in `cli.py`:

```python
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
```

**Step 4: Run tests — expect PASS**

**Step 5: Commit**

```bash
git add src/fakturoid_connector/reports.py src/fakturoid_connector/cli.py
git commit -m "feat: monthly and yearly report generation"
```

---

### Task 7: Discord Notifications

**Files:**
- Create: `src/fakturoid_connector/notifications.py`
- Modify: `src/fakturoid_connector/cli.py`
- Create: `tests/test_notifications.py`

**Step 1: Write failing test**

```python
from unittest.mock import patch, MagicMock
from fakturoid_connector.notifications import build_due_message, send_discord


def test_build_due_message_groups_correctly():
    invoices = [
        {"number": "FV-001", "client_name": "A", "total": "1000", "currency": "CZK",
         "due_on": "2026-03-10", "remaining_amount": "1000", "status": "overdue"},
        {"number": "FV-002", "client_name": "B", "total": "2000", "currency": "CZK",
         "due_on": "2026-03-18", "remaining_amount": "2000", "status": "open"},
    ]
    msg = build_due_message(invoices, today="2026-03-18")
    assert "FV-001" in msg
    assert "FV-002" in msg
```

**Step 2: Run test — expect FAIL**

**Step 3: Implement notifications**

```python
"""Discord webhook notifications for invoice due dates."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import requests


def build_due_message(invoices: list[dict[str, Any]], *, today: str | None = None) -> str:
    """Build Discord message with overdue/due today/due soon invoices."""
    today_date = datetime.strptime(today, "%Y-%m-%d").date() if today else date.today()

    overdue = []
    due_today = []
    due_soon = []  # within 3 days

    for inv in invoices:
        if inv.get("status") in ("paid", "cancelled"):
            continue
        due_on = inv.get("due_on")
        if not due_on:
            continue
        due_date = datetime.strptime(due_on, "%Y-%m-%d").date()
        diff = (due_date - today_date).days

        entry = (
            f"  • {inv['number']} | {inv.get('client_name', '?')} | "
            f"{inv.get('remaining_amount', inv.get('total', '?'))} {inv.get('currency', 'CZK')}"
        )

        if diff < 0:
            overdue.append(f"{entry} | {abs(diff)} dní po splatnosti")
        elif diff == 0:
            due_today.append(entry)
        elif diff <= 3:
            label = "zítra" if diff == 1 else f"za {diff} dny"
            due_soon.append(f"{entry} | {label}")

    lines = []
    if overdue:
        lines.append(f"🔴 **Po splatnosti ({len(overdue)}):**")
        lines.extend(overdue)
        lines.append("")
    if due_today:
        lines.append(f"🟡 **Splatné dnes ({len(due_today)}):**")
        lines.extend(due_today)
        lines.append("")
    if due_soon:
        lines.append(f"🟢 **Splatné do 3 dnů ({len(due_soon)}):**")
        lines.extend(due_soon)
        lines.append("")

    if not lines:
        return "✅ Žádné faktury k řešení."

    total_remaining = sum(
        float(inv.get("remaining_amount", 0))
        for inv in invoices
        if inv.get("status") not in ("paid", "cancelled")
    )
    lines.append(f"💰 **Celkem nezaplaceno: {total_remaining:,.0f} CZK**")

    return "\n".join(lines)


def send_discord(webhook_url: str, message: str) -> None:
    """Send a message to Discord via webhook."""
    resp = requests.post(webhook_url, json={"content": message})
    resp.raise_for_status()
```

Add `check-due` CLI command:

```python
@cli.command("check-due")
def check_due():
    """Check due invoices and send Discord notification."""
    from fakturoid_connector.notifications import build_due_message, send_discord
    client = _get_client()
    invoices_data = client.list_invoices()
    message = build_due_message(invoices_data)
    click.echo(message)

    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if webhook_url:
        send_discord(webhook_url, message)
        click.echo("\nDiscord notification sent.")
    else:
        click.echo("\nDISCORD_WEBHOOK_URL not set, skipping notification.")
```

**Step 4: Run tests — expect PASS**

**Step 5: Commit**

```bash
git add src/fakturoid_connector/notifications.py tests/test_notifications.py src/fakturoid_connector/cli.py
git commit -m "feat: Discord webhook notifications for due invoices"
```

---

### Task 8: MCP Server

**Files:**
- Create: `src/fakturoid_connector/mcp_server.py`

**Step 1: Implement MCP server**

```python
"""MCP Server for Fakturoid — exposes tools for Claude Code."""

from __future__ import annotations

import json
import os

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
    """Create a new invoice. Lines should have 'name', 'unit_price', 'quantity'."""
    client = _get_client()
    data = {
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
    """List or search contacts/clients."""
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
    """Get full detail of a contact/client."""
    client = _get_client()
    return json.dumps(client.get_subject(subject_id), indent=2, ensure_ascii=False)


@mcp.tool()
def get_account_summary() -> str:
    """Get account overview: stats, overdue amounts, unpaid totals."""
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
    """Download invoice PDF to local file."""
    import pathlib
    client = _get_client()
    inv = client.get_invoice(invoice_id)
    pdf = client.download_invoice_pdf(invoice_id)
    if pdf is None:
        return "PDF not ready yet."
    path = pathlib.Path(output_dir)
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
```

**Step 2: Test MCP server starts**

```bash
python -m fakturoid_connector.mcp_server
```

**Step 3: Commit**

```bash
git add src/fakturoid_connector/mcp_server.py
git commit -m "feat: MCP server with 10 tools for Claude Code"
```

---

### Task 9: Skill File

**Files:**
- Create: `skills/fakturoid-connector/SKILL.md`

**Step 1: Write skill file**

```markdown
---
name: fakturoid-connector
description: Use when working with Fakturoid.cz — invoices, contacts, expenses,
  reports, or when user mentions Fakturoid, faktury, fakturace, splatnost.
  Use when user mentions invoice management, billing, or Czech accounting.
---

# Fakturoid Connector

CLI tool and MCP server for Fakturoid.cz invoice management.

## When to use CLI vs MCP

- **MCP tools**: Use when in Claude Code conversation for natural language queries
- **CLI**: Use for automation, cron jobs, batch operations, or when MCP is unavailable

## CLI Commands

```bash
fakturoid search "query"              # Search invoices
fakturoid invoices --overdue          # Overdue invoices
fakturoid invoices --unpaid           # Unpaid invoices
fakturoid invoice <ID>                # Invoice detail
fakturoid contacts                    # List contacts
fakturoid export --format csv -o .    # Export invoices
fakturoid export-pdf <ID> -o .        # Download PDF
fakturoid report monthly              # Monthly report
fakturoid report yearly               # Yearly report
fakturoid check-due                   # Check due dates + Discord notify
fakturoid summary                     # Account overview
```

## Setup

Requires `.env` in project root:
```
FAKTUROID_CLIENT_ID=...
FAKTUROID_CLIENT_SECRET=...
FAKTUROID_SLUG=continerocorp
DISCORD_WEBHOOK_URL=...
```

## MCP Server

Add to Claude Code settings:
```json
{
  "mcpServers": {
    "fakturoid": {
      "command": "python",
      "args": ["-m", "fakturoid_connector.mcp_server"],
      "cwd": "/Users/fogl/Documents/PROJECTS/fakturoid-connector"
    }
  }
}
```
```

**Step 2: Commit**

```bash
git add skills/
git commit -m "feat: Claude Code skill for fakturoid-connector"
```

---

### Task 10: Setup .env and Integration Test

**Step 1: Create .env with real credentials**

```bash
# Create .env with actual values (manually, not committed)
```

**Step 2: Install package**

```bash
cd /Users/fogl/Documents/PROJECTS/fakturoid-connector
pip install -e .
```

**Step 3: Test real API connection**

```bash
fakturoid summary
fakturoid invoices --overdue
fakturoid contacts
```

**Step 4: Test MCP server**

```bash
python -m fakturoid_connector.mcp_server
```

**Step 5: Final commit and push**

```bash
git push origin main
```
