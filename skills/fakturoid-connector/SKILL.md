---
name: fakturoid-connector
description: Use when working with Fakturoid.cz — invoices, contacts, expenses,
  reports, or when user mentions Fakturoid, faktury, fakturace, splatnost, billing.
  Use when user mentions invoice management or Czech accounting.
---

# Fakturoid Connector

CLI tool and MCP server for Fakturoid.cz invoice management.

## When to use CLI vs MCP

- **MCP tools**: Use in Claude Code conversations for natural language queries
- **CLI**: Use for automation, cron jobs, batch operations, or when MCP is unavailable

## CLI Commands

```bash
fakturoid search "query"              # Search invoices by text
fakturoid invoices                    # List all invoices
fakturoid invoices --overdue          # Overdue invoices only
fakturoid invoices --unpaid           # Unpaid invoices only
fakturoid invoice <ID>                # Invoice detail (JSON)
fakturoid contacts                    # List all contacts
fakturoid export --format json -o .   # Export invoices to JSON
fakturoid export --format csv -o .    # Export invoices to CSV
fakturoid export-pdf <ID> -o .        # Download invoice PDF
fakturoid report monthly              # Current month report
fakturoid report monthly --year 2025 --month 12
fakturoid report yearly               # Current year report
fakturoid report yearly --year 2025
fakturoid check-due                   # Check due dates + Discord notify
fakturoid summary                     # Account overview
fakturoid abo                         # ABO payment file (expenses due today)
fakturoid abo --due-date 2026-03-21   # ABO for expenses due by date
fakturoid abo --due-date 2026-03-21 -o ~/Downloads
```

## Examples

User: "Jaké faktury jsou po splatnosti?"
→ `fakturoid invoices --overdue`

User: "Kolik mi dluží firma X?"
→ `fakturoid search "X"`

User: "Dej mi přehled za březen"
→ `fakturoid report monthly --year 2026 --month 3`

User: "Co musím dnes zaplatit?"
→ `fakturoid check-due`

User: "Vytvoř ABO na náklady splatné do pátku"
→ `fakturoid abo --due-date 2026-03-21`

## Setup

Requires `.env` in project root:
```
FAKTUROID_CLIENT_ID=your_client_id
FAKTUROID_CLIENT_SECRET=your_client_secret
FAKTUROID_SLUG=your_account_slug
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# ABO payment orders (optional)
FAKTUROID_SENDER_ACCOUNT=000000-1234567890/0100
FAKTUROID_SENDER_NAME=Your Company Name
FAKTUROID_SENDER_ICO=12345678
```

## MCP Server

Add to `.mcp.json`:
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
