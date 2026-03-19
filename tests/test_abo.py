"""Tests for ABO file generation.

Tests verify compliance with the official ABO format specification:
"Technical Description of the ABO Format Structure for Programmers" (3-2267a)
by Česká spořitelna.
"""

from datetime import date

import pytest

from fakturoid_connector.abo import generate_abo, _parse_account


# ── Account parsing ──────────────────────────────────────────────


class TestParseAccount:
    def test_with_prefix(self):
        prefix, number, bank = _parse_account("000131-2733070267/0100")
        assert prefix == "000131"
        assert number == "2733070267"
        assert bank == "0100"

    def test_without_prefix(self):
        prefix, number, bank = _parse_account("1234567890/0100")
        assert prefix == "0"
        assert number == "1234567890"
        assert bank == "0100"

    def test_with_spaces(self):
        prefix, number, bank = _parse_account(" 1234567890 / 2010 ")
        assert number == "1234567890"
        assert bank == "2010"

    def test_invalid_no_slash(self):
        with pytest.raises(ValueError, match="missing /"):
            _parse_account("1234567890")


# ── Empty / invalid input ────────────────────────────────────────


class TestGenerateAboEdgeCases:
    def test_empty_list(self):
        assert generate_abo([], sender_account="123/0100") == ""

    def test_no_bank_account(self):
        expenses = [{"bank_account": "", "total": 1000}]
        assert generate_abo(expenses, sender_account="123/0100") == ""

    def test_missing_bank_account_key(self):
        expenses = [{"total": 1000}]
        assert generate_abo(expenses, sender_account="123/0100") == ""

    def test_zero_amount_skipped(self):
        expenses = [{"bank_account": "111/0100", "total": 0}]
        assert generate_abo(expenses, sender_account="123/0100") == ""

    def test_negative_amount_skipped(self):
        expenses = [{"bank_account": "111/0100", "total": -500}]
        assert generate_abo(expenses, sender_account="123/0100") == ""


# ── UHL1 Record (spec page 2) ───────────────────────────────────


class TestUHL1Record:
    """UHL1: message_type(4) + date(6) + name(20) + client_number(10)
    + interval_start(3) + interval_end(3) + code_fixed(6) + code_secret(6) + CRLF
    Total: 58 chars + CRLF
    """

    def _get_uhl(self, **kwargs) -> str:
        defaults = {
            "expenses": [{"bank_account": "111/0100", "total": 100}],
            "sender_account": "000000-9876543210/0800",
            "sender_name": "Test Firma s.r.o.",
            "payment_date": date(2026, 3, 19),
        }
        defaults.update(kwargs)
        expenses = defaults.pop("expenses")
        result = generate_abo(expenses, **defaults)
        return result.split("\r\n")[0]

    def test_starts_with_uhl1(self):
        uhl = self._get_uhl()
        assert uhl[:4] == "UHL1"

    def test_date_ddmmyy(self):
        uhl = self._get_uhl(payment_date=date(2026, 3, 19))
        assert uhl[4:10] == "190326"

    def test_client_name_20_chars_padded(self):
        uhl = self._get_uhl(sender_name="Test")
        name_field = uhl[10:30]
        assert len(name_field) == 20
        assert name_field == "TEST                "

    def test_client_name_truncated_to_20(self):
        uhl = self._get_uhl(sender_name="A Very Long Company Name That Exceeds")
        name_field = uhl[10:30]
        assert len(name_field) == 20

    def test_client_number_10_digits(self):
        """Client number = account number without prefix, 10 digits."""
        uhl = self._get_uhl(sender_account="000000-9876543210/0800")
        client_number = uhl[30:40]
        assert client_number == "9876543210"
        assert len(client_number) == 10

    def test_intervals_and_codes(self):
        """After client number: interval_start(3) + interval_end(3) + fixed(6) + secret(6)."""
        uhl = self._get_uhl()
        remainder = uhl[40:]
        assert len(remainder) == 18  # 3+3+6+6

    def test_total_length(self):
        uhl = self._get_uhl()
        assert len(uhl) == 58  # 4+6+20+10+3+3+6+6


# ── Accounting File Header (spec page 2) ────────────────────────


class TestAccountingFileHeader:
    """Format: '1' SP type(4) SP file_number(6) SP bank_code(4) CRLF"""

    def _get_header(self, **kwargs) -> str:
        defaults = {
            "expenses": [{"bank_account": "111/0100", "total": 100}],
            "sender_account": "000000-1234567890/2010",
            "payment_date": date(2026, 1, 1),
        }
        defaults.update(kwargs)
        expenses = defaults.pop("expenses")
        result = generate_abo(expenses, **defaults)
        return result.split("\r\n")[1]

    def test_starts_with_1(self):
        header = self._get_header()
        assert header[0] == "1"

    def test_type_is_1501_for_payment_orders(self):
        """Type of data must be 1501 for payment orders (spec comment 1)."""
        header = self._get_header()
        assert header[2:6] == "1501"

    def test_file_number_6_digits(self):
        header = self._get_header()
        file_num = header[7:13]
        assert len(file_num) == 6
        assert file_num.isdigit()

    def test_bank_code(self):
        header = self._get_header(sender_account="123/2010")
        assert header.endswith("2010")

    def test_bank_code_0800(self):
        header = self._get_header(sender_account="123/0800")
        assert header.endswith("0800")


# ── Group Header (spec page 3) ──────────────────────────────────


class TestGroupHeader:
    """Format: '2' SP payer_account SP total_amount SP due_date CRLF"""

    def _get_group(self, **kwargs) -> str:
        defaults = {
            "expenses": [{"bank_account": "111/0100", "total": 1000.50}],
            "sender_account": "000000-1234567890/0800",
            "payment_date": date(2026, 3, 17),
        }
        defaults.update(kwargs)
        expenses = defaults.pop("expenses")
        result = generate_abo(expenses, **defaults)
        return result.split("\r\n")[2]

    def test_starts_with_2(self):
        group = self._get_group()
        assert group[0] == "2"

    def test_payer_account_with_prefix(self):
        group = self._get_group(sender_account="000131-1234567890/0800")
        assert "000131-1234567890" in group

    def test_payer_account_zero_prefix(self):
        group = self._get_group(sender_account="1234567890/0800")
        assert "000000-1234567890" in group

    def test_amount_in_hellers(self):
        """Amount is in hellers (last two chars are cents). 1000.50 = 100050 hellers."""
        group = self._get_group(
            expenses=[{"bank_account": "111/0100", "total": 1000.50}]
        )
        assert "100050" in group

    def test_total_is_sum_of_all(self):
        """Total should be sum of all valid expenses."""
        expenses = [
            {"bank_account": "111/0100", "total": 1000},
            {"bank_account": "222/0200", "total": 2500.75},
        ]
        group = self._get_group(expenses=expenses)
        # 1000*100 + 2500.75*100 = 100000 + 250075 = 350075
        assert "350075" in group

    def test_due_date_ddmmyy(self):
        group = self._get_group(payment_date=date(2026, 3, 17))
        assert group.endswith("170326")


# ── Payment Item (spec page 4) ──────────────────────────────────


class TestPaymentItem:
    """Batch payment item (no debit account):
    credit_account SP amount SP vs SP ks SP ss SP message CRLF
    """

    def _get_item(self, expense=None, **kwargs) -> str:
        expense = expense or {
            "bank_account": "000131-2733070267/0710",
            "total": 94996.70,
            "variable_symbol": "202604",
        }
        defaults = {
            "expenses": [expense],
            "sender_account": "000000-1234567890/0800",
            "sender_name": "Test Firma",
            "sender_ico": "12345678",
            "payment_date": date(2026, 3, 19),
        }
        defaults.update(kwargs)
        expenses = defaults.pop("expenses")
        result = generate_abo(expenses, **defaults)
        # Item is line index 3 (after UHL, header, group)
        return result.split("\r\n")[3]

    def test_credit_account_with_prefix(self):
        item = self._get_item({"bank_account": "000131-2733070267/0710", "total": 100})
        assert "000131-2733070267" in item

    def test_credit_account_zero_prefix(self):
        item = self._get_item({"bank_account": "1234567890/0100", "total": 100})
        assert "000000-1234567890" in item

    def test_amount_in_hellers_12_digits(self):
        """Amount in hellers, max 12 digits (spec seq 5)."""
        item = self._get_item({"bank_account": "111/0100", "total": 94996.70})
        # 94996.70 * 100 = 9499670 hellers, padded to 12
        assert "009499670" in item

    def test_variable_symbol_10_digits(self):
        """VS padded to 10 digits (spec seq 7)."""
        item = self._get_item({
            "bank_account": "111/0100", "total": 100, "variable_symbol": "202604"
        })
        assert "0000202604" in item

    def test_variable_symbol_empty_defaults_to_zero(self):
        item = self._get_item({"bank_account": "111/0100", "total": 100})
        assert "0000000000" in item

    def test_constant_symbol_format(self):
        """KS field (10 chars): bank code at positions 5-8 from right,
        KS at positions 1-4 from right. Fakturoid uses '05' prefix."""
        item = self._get_item({"bank_account": "111/3030", "total": 100})
        assert "0530300000" in item

    def test_constant_symbol_bank_0710(self):
        item = self._get_item({"bank_account": "111/0710", "total": 100})
        assert "0507100000" in item

    def test_constant_symbol_bank_5500(self):
        item = self._get_item({"bank_account": "111/5500", "total": 100})
        assert "0555000000" in item

    def test_constant_symbol_bank_6210(self):
        item = self._get_item({"bank_account": "111/6210", "total": 100})
        assert "0562100000" in item

    def test_specific_symbol_zeros(self):
        """SS field should be 10 zeros."""
        item = self._get_item({"bank_account": "111/0100", "total": 100})
        parts = item.split(" ")
        # SS is the 5th space-separated field (index 4)
        assert "0000000000" in item

    def test_av_message(self):
        item = self._get_item(
            {"bank_account": "111/0100", "total": 100},
            sender_name="Moje Firma",
            sender_ico="99887766",
        )
        assert "AV:Moje Firma, IC 99887766" in item

    def test_av_message_name_only(self):
        item = self._get_item(
            {"bank_account": "111/0100", "total": 100},
            sender_name="Firma",
            sender_ico="",
        )
        assert "AV:Firma" in item
        assert "IC" not in item

    def test_no_av_when_no_name(self):
        item = self._get_item(
            {"bank_account": "111/0100", "total": 100},
            sender_name="",
            sender_ico="",
        )
        assert "AV:" not in item


# ── Footer records (spec page 3) ────────────────────────────────


class TestFooter:
    def _get_lines(self) -> list[str]:
        result = generate_abo(
            [{"bank_account": "111/0100", "total": 100}],
            sender_account="123/0800",
            payment_date=date(2026, 1, 1),
        )
        return result.split("\r\n")

    def test_end_of_group(self):
        """End of group: '3' SP '+' CRLF"""
        lines = self._get_lines()
        assert lines[-3] == "3 +"

    def test_end_of_accounting_file(self):
        """End of accounting file: '5' SP '+' CRLF"""
        lines = self._get_lines()
        assert lines[-2] == "5 +"

    def test_crlf_line_endings(self):
        result = generate_abo(
            [{"bank_account": "111/0100", "total": 100}],
            sender_account="123/0800",
        )
        assert "\r\n" in result
        # No bare LF (every LF must be preceded by CR)
        for i, ch in enumerate(result):
            if ch == "\n":
                assert i > 0 and result[i - 1] == "\r"

    def test_ends_with_crlf(self):
        result = generate_abo(
            [{"bank_account": "111/0100", "total": 100}],
            sender_account="123/0800",
        )
        assert result.endswith("\r\n")


# ── Full structure ───────────────────────────────────────────────


class TestFullStructure:
    def test_correct_line_count(self):
        """1 UHL + 1 header + 1 group + N items + 1 end_group + 1 end_file."""
        expenses = [
            {"bank_account": "111/0100", "total": 1000},
            {"bank_account": "222/0200", "total": 2000},
            {"bank_account": "333/0300", "total": 3000},
        ]
        result = generate_abo(expenses, sender_account="999/0800", payment_date=date(2026, 1, 1))
        lines = [l for l in result.split("\r\n") if l]  # exclude trailing empty
        # UHL + header + group + 3 items + end_group + end_file = 8
        assert len(lines) == 8

    def test_record_order(self):
        result = generate_abo(
            [{"bank_account": "111/0100", "total": 100}],
            sender_account="999/0800",
            payment_date=date(2026, 1, 1),
        )
        lines = [l for l in result.split("\r\n") if l]
        assert lines[0].startswith("UHL1")
        assert lines[1].startswith("1 ")
        assert lines[2].startswith("2 ")
        # Items don't start with a record type number for batch orders
        assert not lines[3].startswith("1 ") and not lines[3].startswith("2 ")
        assert lines[-2] == "3 +"
        assert lines[-1] == "5 +"


# ── Comparison with Fakturoid web output ─────────────────────────


class TestMatchesFakturoidOutput:
    """Verify our output matches the format Fakturoid web generates."""

    def test_payment_line_matches_fakturoid(self):
        """Compare a single payment line against known Fakturoid output.

        Fakturoid line:
        000713-0077628621 000000952500 0007462271 0507100000 0000000000 AV:Continero Corp sro, IC 07462271
        """
        expense = {
            "bank_account": "000713-0077628621/0710",
            "total": 9525.00,
            "variable_symbol": "7462271",
        }
        result = generate_abo(
            [expense],
            sender_account="000000-1234567890/2010",
            sender_name="Continero Corp sro",
            sender_ico="07462271",
            payment_date=date(2026, 3, 19),
        )
        item_line = result.split("\r\n")[3]

        assert item_line == (
            "000713-0077628621 "
            "000000952500 "
            "0007462271 "
            "0507100000 "
            "0000000000 "
            "AV:Continero Corp sro, IC 07462271"
        )

    def test_group_header_matches_fakturoid(self):
        """Fakturoid group: 2 000000-2301502986 00000015436000 190326"""
        expenses = [
            {"bank_account": "111/0710", "total": 9525.00},
            {"bank_account": "222/0710", "total": 36641.00},
            {"bank_account": "333/0710", "total": 3344.00},
            {"bank_account": "444/5500", "total": 46673.00},
            {"bank_account": "555/6210", "total": 24590.00},
            {"bank_account": "666/3030", "total": 680.00},
            {"bank_account": "777/3030", "total": 20744.00},
            {"bank_account": "888/0710", "total": 12163.00},
        ]
        total = sum(e["total"] for e in expenses)
        total_hellers = round(total * 100)

        result = generate_abo(
            expenses,
            sender_account="000000-1234567890/2010",
            payment_date=date(2026, 3, 19),
        )
        group_line = result.split("\r\n")[2]

        assert group_line.startswith("2 000000-1234567890 ")
        assert group_line.endswith(" 190326")
        assert f"{total_hellers:014d}" in group_line

    def test_accounting_header_type_1501(self):
        """Fakturoid uses 1501 (payment orders), not 1502 (direct debits)."""
        result = generate_abo(
            [{"bank_account": "111/0100", "total": 100}],
            sender_account="123/2010",
            payment_date=date(2026, 1, 1),
        )
        header = result.split("\r\n")[1]
        assert header == "1 1501 001000 2010"
