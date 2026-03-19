"""Tests for ABO file generation."""

from datetime import date

from fakturoid_connector.abo import generate_abo, _parse_account


def test_parse_account_with_prefix():
    prefix, number, bank = _parse_account("000131-2733070267/0100")
    assert prefix == "000131"
    assert number == "2733070267"
    assert bank == "0100"


def test_parse_account_without_prefix():
    prefix, number, bank = _parse_account("1234567890/0100")
    assert prefix == "0"
    assert number == "1234567890"
    assert bank == "0100"


def test_generate_abo_basic():
    expenses = [
        {
            "number": "N-001",
            "bank_account": "0108849508/0501",
            "total": 114360.00,
            "variable_symbol": "20260201",
            "constant_symbol": "0",
            "supplier_name": "Test Supplier",
        },
    ]
    result = generate_abo(
        expenses,
        sender_account="000000-1234567890/0100",
        sender_name="Test Company",
        sender_ico="12345678",
        payment_date=date(2026, 3, 17),
    )
    lines = result.strip().split("\r\n")

    # UHL header
    assert lines[0].startswith("UHL1170326")
    assert "TEST COMPANY" in lines[0]

    # Batch header
    assert "0100" in lines[1]

    # Group record
    assert "000000-1234567890" in lines[2]
    assert "170326" in lines[2]

    # Payment line
    assert "000000-0108849508" in lines[3]
    assert "011436000" in lines[3]  # amount in hellers
    assert "0020260201" in lines[3]  # variable symbol
    assert "AV:Test Company, IC 12345678" in lines[3]

    # Footer
    assert lines[-2] == "3 +"
    assert lines[-1] == "5 +"


def test_generate_abo_empty():
    assert generate_abo([], sender_account="123/0100") == ""


def test_generate_abo_skips_no_bank_account():
    expenses = [
        {"number": "N-001", "bank_account": "", "total": 1000},
        {"number": "N-002", "total": 2000},
    ]
    result = generate_abo(expenses, sender_account="123/0100")
    assert result == ""


def test_generate_abo_multiple():
    expenses = [
        {"bank_account": "111/0100", "total": 1000.00, "variable_symbol": "1"},
        {"bank_account": "222/0200", "total": 2000.50, "variable_symbol": "2"},
    ]
    result = generate_abo(
        expenses,
        sender_account="999/0300",
        payment_date=date(2026, 1, 15),
    )
    lines = result.strip().split("\r\n")
    # 1 UHL + 1 batch + 1 group + 2 payments + 2 footer = 7 lines
    assert len(lines) == 7
    # Total in group record should be 300050 hellers
    assert "00000300050" in lines[2]
