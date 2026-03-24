# Fakturoid Connector

Faktura vám řekne, co se stalo. Tenhle connector vám řekne, co s tím.

Open-source CLI, MCP server a Discord notifikace pro [Fakturoid.cz](https://www.fakturoid.cz/). Ptáte se AI asistenta na faktury, generujete platební příkazy, dostáváte denní připomínky splatností. Bez otevírání prohlížeče.

> *"Kolik nám dluží klient X?" / "Vygeneruj platební příkaz na splatné faktury." / "Jaké faktury jsou po splatnosti?"*
>
> Ptáte se přirozeně, Claude sahá přímo do Fakturoid.

## Proč to existuje

Fakturoid je skvělý na fakturaci. Ale zjistit, kdo zaplatil, co je po splatnosti a co ještě musí odejít, to je pořád proklikávání webového rozhraní.

Tenhle connector z Fakturoid udělá něco, s čím se dá mluvit. Přes [Claude Code](https://claude.ai/claude-code) (MCP server) nebo terminál (CLI) máte přímý přístup k fakturám, nákladům, kontaktům, reportům a platebním souborům.

V kombinaci s [Fio Connectorem](https://github.com/Continero/fio-connector) pro bankovní data dostanete kompletní obraz: co bylo fakturováno, co bylo zaplaceno, co je ještě otevřené.

## Co umí

| | |
|---|---|
| CLI | Hledání faktur, kontakty, export dat, reporty, ABO platební příkazy |
| MCP Server | 11 nástrojů pro Claude Code a další MCP-kompatibilní AI asistenty |
| ABO platby | Generování platebních souborů z nezaplacených nákladů, nahrajete do banky a je to |
| Discord upozornění | Denní notifikace o splatnostech, rozdělené na pohledávky, závazky a inkaso |
| Fakturoid API v3 | OAuth 2 Client Credentials s automatickým obnovením tokenu a stránkováním |

## Začínáme

### 1. Instalace

```bash
pip install git+https://github.com/Continero/fakturoid-connector.git
```

Nebo klonovat a nainstalovat v editovatelném režimu:

```bash
git clone https://github.com/Continero/fakturoid-connector.git
cd fakturoid-connector
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Konfigurace

```bash
cp .env.example .env
```

Vyplňte přístupové údaje k Fakturoid API:

```env
FAKTUROID_CLIENT_ID=your_client_id
FAKTUROID_CLIENT_SECRET=your_client_secret
FAKTUROID_SLUG=your_account_slug
```

Kde je najdete:

1. Přihlaste se na [app.fakturoid.cz](https://app.fakturoid.cz/)
2. Nastavení -> Uživatelský účet -> API
3. Vytvořte novou aplikaci, dostanete Client ID a Client Secret
4. Slug je subdoména ve vašem Fakturoid URL: `app.fakturoid.cz/api/v3/accounts/{slug}/...`

### 3. Použití

```bash
fakturoid summary              # přehled účtu
fakturoid invoices --overdue   # co je po splatnosti
fakturoid search "Acme"        # hledání faktur
```

## CLI příkazy

### Faktury

```bash
fakturoid invoices                    # všechny faktury
fakturoid invoices --overdue          # po splatnosti
fakturoid invoices --unpaid           # nezaplacené
fakturoid invoices --status paid      # filtr podle statusu

fakturoid search "dotaz"              # fulltextové hledání
fakturoid invoice 12345               # detail faktury (JSON)
```

### Kontakty

```bash
fakturoid contacts                    # seznam kontaktů
```

### Reporty

```bash
fakturoid report monthly              # aktuální měsíc
fakturoid report monthly --year 2025 --month 12
fakturoid report yearly               # aktuální rok
fakturoid report yearly --year 2025
```

Výstupem jsou markdown tabulky s počty faktur, obratem a rozpisem zaplacených/nezaplacených.

### Export

```bash
fakturoid export --format json -o ./output
fakturoid export --format csv -o ./output
fakturoid export-pdf 12345 -o ./output    # stažení PDF faktury
```

### Účet

```bash
fakturoid summary    # tarif, počet faktur, nezaplacené, po splatnosti, částky
```

### ABO platební příkazy

Generuje platební soubory ve formátu ABO z nezaplacených nákladů ve Fakturoid. Soubor `.abo` nahrajete do internetového bankovnictví a zaplatíte hromadně.

```bash
fakturoid abo                         # náklady splatné dnes
fakturoid abo --due-date 2026-03-28   # náklady splatné do data
fakturoid abo -o ~/Downloads          # vlastní výstupní adresář
```

Vyžaduje tři další proměnné v `.env`:

```env
FAKTUROID_SENDER_ACCOUNT=000000-1234567890/0100   # váš bankovní účet
FAKTUROID_SENDER_NAME=Nazev Firmy s.r.o.
FAKTUROID_SENDER_ICO=12345678
```

Generovaný ABO soubor odpovídá specifikaci českého bankovního formátu (3-2267a). Funguje s Fio, KB, ČSOB, Raiffeisen a dalšími bankami.

### Discord notifikace

```bash
fakturoid check-due
```

Pošle strukturovanou zprávu na Discord se třemi sekcemi:

- FAKTURY -- pohledávky (co mají klienti zaplatit vám): po splatnosti, splatné dnes, splatné do 3 dnů
- NÁKLADY -- závazky (co musíte zaplatit vy): po splatnosti, splatné dnes, splatné do 3 dnů
- INKASO -- strhne se samo (náklady s tagem `inkaso` ve Fakturoid): po splatnosti, splatné dnes, splatné do 3 dnů

Každá sekce ukazuje součty po měnách. Náklady označené tagem `inkaso` se automaticky oddělí, takže hned vidíte, co vyžaduje ruční akci.

Pro zapnutí nastavte `DISCORD_WEBHOOK_URL` v `.env`:

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

#### Cron

Kontrola splatností každé ráno v 8:00:

```bash
0 8 * * * cd /path/to/fakturoid-connector && .venv/bin/fakturoid check-due
```

## MCP Server (napojení na AI)

MCP server zpřístupňuje data z Fakturoid jako nástroje pro [Claude Code](https://claude.ai/claude-code) a další MCP-kompatibilní AI asistenty.

### Nastavení

Přidejte do `.mcp.json` nebo do konfigurace Claude Code:

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

### Dostupné nástroje

| Nástroj | Popis |
|---------|-------|
| `search_invoices` | Fulltextové hledání faktur |
| `get_invoice` | Detail faktury podle ID |
| `list_overdue_invoices` | Faktury po splatnosti |
| `list_unpaid_invoices` | Nezaplacené faktury |
| `create_invoice` | Vystavení nové faktury s položkami |
| `list_contacts` | Seznam nebo hledání kontaktů |
| `get_contact` | Detail kontaktu podle ID |
| `get_account_summary` | Statistiky účtu, nezaplacené a po splatnosti |
| `download_invoice_pdf` | Stažení faktury jako PDF |
| `list_expenses` | Náklady s volitelným filtrem statusu |
| `generate_abo_file` | ABO platební příkaz z nezaplacených nákladů |

### Příklady dotazů

Po připojení se ptáte běžnou řečí:

- *"Jaké faktury jsou po splatnosti?"*
- *"Kolik nám dluží Acme Corp?"*
- *"Ukaž nezaplacené faktury nad 50 000 Kč"*
- *"Vystav fakturu pro klienta 42 -- konzultace, 10 hodin po 2 000 Kč"*
- *"Stáhni PDF faktury FV-2025-042"*
- *"Vygeneruj ABO platební soubor pro náklady splatné tento pátek"*
- *"Kolik máme celkem nesplacených pohledávek?"*

## Konfigurace

Veškerá konfigurace je přes proměnné prostředí (soubor `.env`):

| Proměnná | Povinná | Popis |
|----------|:-------:|-------|
| `FAKTUROID_CLIENT_ID` | ano | OAuth 2 Client ID z nastavení Fakturoid API |
| `FAKTUROID_CLIENT_SECRET` | ano | OAuth 2 Client Secret |
| `FAKTUROID_SLUG` | ano | Slug vašeho Fakturoid účtu |
| `DISCORD_WEBHOOK_URL` | ne | Discord webhook pro notifikace z `check-due` |
| `FAKTUROID_SENDER_ACCOUNT` | ne | Bankovní účet pro ABO soubory (`prefix-číslo/kód_banky`) |
| `FAKTUROID_SENDER_NAME` | ne | Název firmy pro zprávu v ABO platbě |
| `FAKTUROID_SENDER_ICO` | ne | IČO firmy pro zprávu v ABO platbě |

## Pokrytí API

Postaveno na [Fakturoid API v3](https://www.fakturoid.cz/api/v3):

| Zdroj | Seznam | Hledání | Detail | Vytvoření | Úprava | PDF |
|-------|:------:|:-------:|:------:|:---------:|:------:|:---:|
| Faktury | ano | ano | ano | ano | ano | ano |
| Kontakty | ano | ano | ano | ano | -- | -- |
| Náklady | ano | ano | ano | -- | -- | -- |
| Účet | -- | -- | ano | -- | -- | -- |
| Akce na fakturách (fire) | -- | -- | -- | ano | -- | -- |

Všechny seznamové endpointy automaticky stránkují (40 položek na stránku), takže dostanete kompletní data.

### Zatím neimplementováno

Pull requesty vítány:

- Platby faktur, zprávy k fakturám, platby nákladů
- Generátory a opakované generátory (šablony)
- Události (audit log), úkoly, uživatelé
- Bankovní účty, číselné řady
- Skladové položky a pohyby
- Příchozí soubory, webhooky

## Struktura projektu

```
fakturoid-connector/
├── src/fakturoid_connector/
│   ├── client.py           # Fakturoid API v3 klient (OAuth 2, auto-stránkování)
│   ├── cli.py              # Click CLI (faktury, kontakty, reporty, ABO, check-due)
│   ├── mcp_server.py       # MCP server s 11 nástroji pro AI asistenty
│   ├── notifications.py    # Discord webhook -- upozornění na splatnosti
│   ├── reports.py          # Generování měsíčních/ročních reportů
│   └── abo.py              # Generátor ABO platebních souborů
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

## Vývoj

```bash
git clone https://github.com/Continero/fakturoid-connector.git
cd fakturoid-connector
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pytest
```

Spuštění testů:

```bash
python -m pytest tests/ -v
```

Testy používají mockované API odpovědi, pro vývoj nepotřebujete Fakturoid účet.

## Související projekty

- [Fio Connector](https://github.com/Continero/fio-connector) -- CLI + MCP server pro Fio banku (transakce, kategorie, reporty, platební příkazy)
- [Fakturoid.cz](https://www.fakturoid.cz/) -- česká fakturační platforma
- [Fakturoid API v3 dokumentace](https://www.fakturoid.cz/api/v3)
- [Claude Code](https://claude.ai/claude-code) -- AI asistent s podporou MCP
- [MCP specifikace](https://modelcontextprotocol.io/)

## Licence

MIT -- viz [LICENSE](LICENSE).
