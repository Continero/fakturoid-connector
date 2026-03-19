# Fakturoid Connector

CLI tool, MCP server, and Discord notifier for [Fakturoid.cz](https://www.fakturoid.cz/) — the Czech invoicing platform.

Built for business owners who want to manage invoices, track due dates, and get payment reminders without leaving the terminal or their AI assistant.

## Features

- **CLI** — search invoices, list contacts, export data, generate reports, create ABO payment files
- **MCP Server** — 11 tools for [Claude Code](https://claude.ai/claude-code) and other MCP-compatible AI assistants
- **ABO payment orders** — generate Czech bank payment files from unpaid expenses
- **Discord notifications** — daily due date alerts split into receivables, payables, and auto-deducted payments
- **Fakturoid API v3** — OAuth 2 Client Credentials with automatic token refresh

## Prerequisites

- Python 3.10+
- A [Fakturoid.cz](https://www.fakturoid.cz/) account with API access
- (Optional) Discord webhook URL for notifications

## Installation

```bash
git clone https://github.com/Continero/fakturoid-connector.git
cd fakturoid-connector
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Or install directly from GitHub:

```bash
pip install git+https://github.com/Continero/fakturoid-connector.git
```

## Configuration

Copy the example and fill in your credentials:

```bash
cp .env.example .env
```

```env
FAKTUROID_CLIENT_ID=your_client_id
FAKTUROID_CLIENT_SECRET=your_client_secret
FAKTUROID_SLUG=your_account_slug
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# ABO payment orders (optional)
FAKTUROID_SENDER_ACCOUNT=000000-1234567890/0100
FAKTUROID_SENDER_NAME=Your Company Name
FAKTUROID_SENDER_ICO=12345678
```

**Where to find your credentials:**

1. Log in to [app.fakturoid.cz](https://app.fakturoid.cz/)
2. Go to **Settings** (Nastaven&iacute;) → **User account** (&Uacute;&#269;et u&#382;ivatele) → **API**
3. Create a new application to get your Client ID and Client Secret
4. Your slug is the subdomain in your Fakturoid URL: `app.fakturoid.cz/api/v3/accounts/{slug}/...`

## CLI Usage

```bash
# Account overview
fakturoid summary

# List invoices
fakturoid invoices                    # all invoices
fakturoid invoices --overdue          # overdue only
fakturoid invoices --unpaid           # unpaid only
fakturoid invoices --status paid      # filter by status

# Search invoices
fakturoid search "Acme Corp"

# Invoice detail
fakturoid invoice 12345

# Contacts
fakturoid contacts

# Export
fakturoid export --format json -o ./output
fakturoid export --format csv -o ./output
fakturoid export-pdf 12345 -o ./output

# Reports
fakturoid report monthly
fakturoid report monthly --year 2025 --month 12
fakturoid report yearly
fakturoid report yearly --year 2025

# Due date check + Discord notification
fakturoid check-due

# ABO payment order file
fakturoid abo                         # expenses due today
fakturoid abo --due-date 2026-03-21   # expenses due by date
fakturoid abo -o ~/Downloads          # custom output directory
```

## Discord Notifications

The `check-due` command sends a structured message to Discord with three sections:

```
FAKTURY — receivables (what clients owe you):
  overdue, due today, due within 3 days

NAKLADY — payables (what you need to pay):
  overdue, due today, due within 3 days

INKASO — auto-deducted (tagged "inkaso" in Fakturoid):
  overdue, due today, due within 3 days
```

Expenses tagged with `inkaso` in Fakturoid are automatically separated into their own section, so you can see at a glance what requires manual action.

Each section shows per-currency totals. Set `DISCORD_WEBHOOK_URL` in `.env` to enable.

## ABO Payment Orders

Generate Czech bank payment files (ABO format) from unpaid Fakturoid expenses. Upload the `.abo` file to your internet banking to create batch payment orders.

```bash
fakturoid abo --due-date 2026-03-21
```

Output:
```
Generating ABO for 6 expenses (due <= 2026-03-21):

  N-044 | Supplier A | 20,744 CZK | due: 2026-03-20
  N-041 | Supplier B | 46,673 CZK | due: 2026-03-20
  ...

Total: 126,426.00 CZK
ABO file saved: output/expenses_2026-03-21.abo
```

Requires three additional `.env` variables:

```env
FAKTUROID_SENDER_ACCOUNT=000000-1234567890/0100   # your bank account (prefix-number/bank_code)
FAKTUROID_SENDER_NAME=Your Company Name            # for AV message in payment
FAKTUROID_SENDER_ICO=12345678                      # your company ICO
```

The generated ABO file follows the official Czech banking format specification (Česká spořitelna 3-2267a) and is compatible with Fio, KB, ČSOB, Raiffeisen, and other Czech banks.

### Cron Setup

Run the due date check every morning at 8:00 AM:

```bash
0 8 * * * cd /path/to/fakturoid-connector && .venv/bin/fakturoid check-due
```

## MCP Server (AI Integration)

The MCP server exposes Fakturoid data as tools for AI assistants like [Claude Code](https://claude.ai/claude-code).

### Available Tools

| Tool | Description |
|------|-------------|
| `search_invoices` | Full-text search across invoices |
| `get_invoice` | Get invoice detail by ID |
| `list_overdue_invoices` | All overdue invoices |
| `list_unpaid_invoices` | All unpaid/open invoices |
| `create_invoice` | Create a new invoice |
| `list_contacts` | List or search contacts |
| `get_contact` | Get contact detail by ID |
| `get_account_summary` | Account stats and totals |
| `download_invoice_pdf` | Download invoice as PDF |
| `list_expenses` | List expenses with optional status filter |
| `generate_abo_file` | Generate ABO payment order from unpaid expenses |

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

Then ask your AI assistant things like:

- *"What invoices are overdue?"*
- *"How much does Acme Corp owe us?"*
- *"Create an invoice for client 42 — consulting, 10 hours at 2000 CZK"*
- *"Download the PDF for invoice 12345"*
- *"Generate ABO payment file for expenses due this Friday"*

## Project Structure

```
fakturoid-connector/
├── src/fakturoid_connector/
│   ├── client.py           # Fakturoid API v3 client (OAuth 2)
│   ├── cli.py              # Click CLI commands
│   ├── mcp_server.py       # MCP server (11 tools)
│   ├── notifications.py    # Discord webhook notifications
│   ├── reports.py          # Monthly/yearly report generation
│   └── abo.py              # ABO payment order file generator
├── tests/
│   ├── test_client.py
│   ├── test_cli.py
│   ├── test_notifications.py
│   ├── test_reports.py
│   └── test_abo.py
├── skills/
│   └── fakturoid-connector/
│       └── SKILL.md        # Claude Code skill definition
├── pyproject.toml
├── .env.example
└── README.md
```

## API Coverage

Built on [Fakturoid API v3](https://www.fakturoid.cz/api/v3). The table below shows which API resources are currently supported:

| Resource | List | Search | Get | Create | Update | PDF |
|----------|:----:|:------:|:---:|:------:|:------:|:---:|
| Invoices | yes | yes | yes | yes | yes | yes |
| Subjects (contacts) | yes | yes | yes | yes | — | — |
| Expenses | yes | yes | yes | — | — | — |
| Account | — | — | yes | — | — | — |
| Invoice actions (fire) | — | — | — | yes | — | — |

### Not yet implemented

The following Fakturoid API v3 resources are not covered yet. Contributions welcome:

- Invoice Payments — record and track payments on invoices
- Invoice Messages — send emails/reminders through Fakturoid
- Expense Payments — record payments on expenses
- Generators — invoice templates
- Recurring Generators — automated repeating invoices
- Events — audit log / activity feed
- Todos — tasks from Fakturoid
- Users — user management
- Bank Accounts — bank account configuration
- Number Formats — document numbering
- Inventory Items & Moves — product catalog and stock
- Inbox Files — uploaded documents
- Webhooks — event subscriptions

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

## License

MIT License. See [LICENSE](LICENSE) for details.

## Links

- [Fakturoid.cz](https://www.fakturoid.cz/) — Czech invoicing platform
- [Fakturoid API v3 docs](https://www.fakturoid.cz/api/v3)
- [Claude Code](https://claude.ai/claude-code) — AI coding assistant with MCP support
- [MCP specification](https://modelcontextprotocol.io/)
