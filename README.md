# Fakturoid Connector

**Invoices tell you what happened. This connector tells you what to do about it.**

Open-source CLI, MCP server, and Discord notifier for [Fakturoid.cz](https://www.fakturoid.cz/) — the Czech invoicing platform. Ask your AI assistant about invoices, generate payment files, and get daily payment reminders — all without opening a browser.

> *"Kolik nám dluží klient X?" / "Vygeneruj platební příkaz na splatné faktury." / "Jaké faktury jsou po splatnosti?"*
>
> You ask naturally, Claude reaches directly into Fakturoid.

## Why

Fakturoid is great for invoicing. But checking who paid, what's overdue, and what needs to go out — that's still clicking around a web UI.

This connector turns Fakturoid into something you can **talk to**. Through [Claude Code](https://claude.ai/claude-code) (MCP server) or the terminal (CLI), you get direct access to invoices, expenses, contacts, reports, and payment files.

Combined with [Fio Connector](https://github.com/Continero/fio-connector) for bank data, you get a complete picture: what was invoiced, what was paid, and what's still open.

## Features

| | |
|---|---|
| **CLI** | Search invoices, list contacts, export data, generate reports, create ABO payment files |
| **MCP Server** | 11 tools for Claude Code and other MCP-compatible AI assistants |
| **ABO Payments** | Generate Czech bank payment files from unpaid expenses — upload to your bank, done |
| **Discord Alerts** | Daily due date notifications split into receivables, payables, and auto-deducted payments |
| **Fakturoid API v3** | OAuth 2 Client Credentials with automatic token refresh and auto-pagination |

## Quick Start

### 1. Install

```bash
pip install git+https://github.com/Continero/fakturoid-connector.git
```

Or clone and install in editable mode:

```bash
git clone https://github.com/Continero/fakturoid-connector.git
cd fakturoid-connector
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Configure

```bash
cp .env.example .env
```

Fill in your Fakturoid API credentials:

```env
FAKTUROID_CLIENT_ID=your_client_id
FAKTUROID_CLIENT_SECRET=your_client_secret
FAKTUROID_SLUG=your_account_slug
```

**Where to get credentials:**

1. Log in to [app.fakturoid.cz](https://app.fakturoid.cz/)
2. Go to **Settings** → **User account** → **API**
3. Create a new application — you'll get Client ID and Client Secret
4. Your slug is the subdomain: `app.fakturoid.cz/api/v3/accounts/{slug}/...`

### 3. Use

```bash
fakturoid summary              # account overview
fakturoid invoices --overdue   # what's past due
fakturoid search "Acme"        # find invoices
```

## CLI Reference

### Invoices

```bash
fakturoid invoices                    # all invoices
fakturoid invoices --overdue          # overdue only
fakturoid invoices --unpaid           # unpaid only
fakturoid invoices --status paid      # filter by status

fakturoid search "query"              # full-text search
fakturoid invoice 12345               # invoice detail (JSON)
```

### Contacts

```bash
fakturoid contacts                    # list all contacts
```

### Reports

```bash
fakturoid report monthly              # current month
fakturoid report monthly --year 2025 --month 12
fakturoid report yearly               # current year
fakturoid report yearly --year 2025
```

Reports output markdown tables with invoice counts, revenue, and paid/unpaid breakdowns.

### Export

```bash
fakturoid export --format json -o ./output
fakturoid export --format csv -o ./output
fakturoid export-pdf 12345 -o ./output    # download invoice PDF
```

### Account

```bash
fakturoid summary    # plan, total invoices, unpaid count, overdue count, amounts
```

### ABO Payment Orders

Generate Czech bank payment files from unpaid Fakturoid expenses. Upload the `.abo` file to your internet banking to pay in batch.

```bash
fakturoid abo                         # expenses due today
fakturoid abo --due-date 2026-03-28   # expenses due by date
fakturoid abo -o ~/Downloads          # custom output directory
```

Requires three additional `.env` variables:

```env
FAKTUROID_SENDER_ACCOUNT=000000-1234567890/0100   # your bank account
FAKTUROID_SENDER_NAME=Your Company Name
FAKTUROID_SENDER_ICO=12345678
```

The generated ABO file follows the Czech banking format specification (3-2267a) and is compatible with Fio, KB, CSOB, Raiffeisen, and other Czech banks.

### Discord Notifications

```bash
fakturoid check-due
```

Sends a structured message to Discord with three sections:

- **FAKTURY** — receivables (what clients owe you): overdue, due today, due within 3 days
- **NAKLADY** — payables (what you need to pay): overdue, due today, due within 3 days
- **INKASO** — auto-deducted (tagged `inkaso` in Fakturoid): overdue, due today, due within 3 days

Each section shows per-currency totals. Expenses tagged with `inkaso` in Fakturoid are automatically separated so you see at a glance what requires manual action.

Set `DISCORD_WEBHOOK_URL` in `.env` to enable:

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

#### Cron Setup

Run the due date check every morning at 8:00 AM:

```bash
0 8 * * * cd /path/to/fakturoid-connector && .venv/bin/fakturoid check-due
```

## MCP Server (AI Integration)

The MCP server exposes Fakturoid data as tools for [Claude Code](https://claude.ai/claude-code) and other MCP-compatible AI assistants.

### Setup

Add to your `.mcp.json` or Claude Code MCP config:

```json
{
  "mcpServers": {
    "fakturoid": {
      "command": "/path/to/fakturoid-connector/.venv/bin/python",
      "args": ["-m", "fakturoid_connector.mcp_server"],
      "cwd": "/path/to/fakturoid-connector"
    }
  }
}
```

### Available Tools

| Tool | Description |
|------|-------------|
| `search_invoices` | Full-text search across invoices |
| `get_invoice` | Get invoice detail by ID |
| `list_overdue_invoices` | All overdue invoices |
| `list_unpaid_invoices` | All unpaid/open invoices |
| `create_invoice` | Create a new invoice with line items |
| `list_contacts` | List or search contacts |
| `get_contact` | Get contact detail by ID |
| `get_account_summary` | Account stats, unpaid/overdue totals |
| `download_invoice_pdf` | Download invoice as PDF |
| `list_expenses` | List expenses with optional status filter |
| `generate_abo_file` | Generate ABO payment order from unpaid expenses |

### Example Prompts

Once connected, ask naturally:

- *"What invoices are overdue?"*
- *"How much does Acme Corp owe us?"*
- *"Show me all unpaid invoices over 50,000 CZK"*
- *"Create an invoice for client 42 — consulting, 10 hours at 2,000 CZK"*
- *"Download the PDF for invoice FV-2025-042"*
- *"Generate ABO payment file for expenses due this Friday"*
- *"What's our total outstanding receivables?"*

## Configuration Reference

All configuration is via environment variables (`.env` file):

| Variable | Required | Description |
|----------|:--------:|-------------|
| `FAKTUROID_CLIENT_ID` | yes | OAuth 2 Client ID from Fakturoid API settings |
| `FAKTUROID_CLIENT_SECRET` | yes | OAuth 2 Client Secret |
| `FAKTUROID_SLUG` | yes | Your Fakturoid account slug |
| `DISCORD_WEBHOOK_URL` | no | Discord webhook for `check-due` notifications |
| `FAKTUROID_SENDER_ACCOUNT` | no | Bank account for ABO files (`prefix-number/bank_code`) |
| `FAKTUROID_SENDER_NAME` | no | Company name for ABO payment messages |
| `FAKTUROID_SENDER_ICO` | no | Company ICO for ABO payment messages |

## API Coverage

Built on [Fakturoid API v3](https://www.fakturoid.cz/api/v3):

| Resource | List | Search | Get | Create | Update | PDF |
|----------|:----:|:------:|:---:|:------:|:------:|:---:|
| Invoices | yes | yes | yes | yes | yes | yes |
| Subjects (contacts) | yes | yes | yes | yes | — | — |
| Expenses | yes | yes | yes | — | — | — |
| Account | — | — | yes | — | — | — |
| Invoice actions (fire) | — | — | — | yes | — | — |

All list endpoints auto-paginate (40 items per page) so you get complete data.

### Not Yet Implemented

Contributions welcome for:

- Invoice Payments, Messages, Expense Payments
- Generators & Recurring Generators (templates)
- Events (audit log), Todos, Users
- Bank Accounts, Number Formats
- Inventory Items & Moves
- Inbox Files, Webhooks

## Project Structure

```
fakturoid-connector/
├── src/fakturoid_connector/
│   ├── client.py           # Fakturoid API v3 client (OAuth 2, auto-pagination)
│   ├── cli.py              # Click CLI (invoices, contacts, reports, ABO, check-due)
│   ├── mcp_server.py       # MCP server with 11 tools for AI assistants
│   ├── notifications.py    # Discord webhook — due date alerts
│   ├── reports.py          # Monthly/yearly report generation
│   └── abo.py              # ABO payment order file generator
├── tests/
│   ├── test_client.py
│   ├── test_cli.py
│   ├── test_notifications.py
│   ├── test_reports.py
│   └── test_abo.py
├── pyproject.toml
├── .env.example
└── README.md
```

## Development

```bash
git clone https://github.com/Continero/fakturoid-connector.git
cd fakturoid-connector
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pytest
```

Run tests:

```bash
python -m pytest tests/ -v
```

All tests use mocked API responses — no Fakturoid account needed for development.

## Related

- **[Fio Connector](https://github.com/Continero/fio-connector)** — CLI + MCP server for Fio banka (transactions, categories, reports, payment orders)
- [Fakturoid.cz](https://www.fakturoid.cz/) — Czech invoicing platform
- [Fakturoid API v3 docs](https://www.fakturoid.cz/api/v3)
- [Claude Code](https://claude.ai/claude-code) — AI coding assistant with MCP support
- [MCP specification](https://modelcontextprotocol.io/)

## License

MIT — see [LICENSE](LICENSE).
