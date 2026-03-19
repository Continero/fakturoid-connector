from fakturoid_connector.notifications import build_due_message

def test_build_due_message_overdue_invoice():
    invoices = [
        {"number": "FV-001", "client_name": "Test", "total": "1000",
         "currency": "CZK", "due_on": "2026-03-10", "remaining_amount": "1000",
         "status": "overdue"},
    ]
    msg = build_due_message(invoices, today="2026-03-18")
    assert "FV-001" in msg
    assert "Po splatnosti" in msg
    assert "FAKTURY" in msg
    assert "dostat" in msg

def test_build_due_message_due_today():
    invoices = [
        {"number": "FV-002", "client_name": "Test", "total": "2000",
         "currency": "CZK", "due_on": "2026-03-18", "remaining_amount": "2000",
         "status": "open"},
    ]
    msg = build_due_message(invoices, today="2026-03-18")
    assert "FV-002" in msg
    assert "dnes" in msg

def test_build_due_message_nothing():
    invoices = [
        {"number": "FV-003", "client_name": "Test", "total": "500",
         "currency": "CZK", "due_on": "2026-03-10", "remaining_amount": "0",
         "status": "paid"},
    ]
    msg = build_due_message(invoices, [], today="2026-03-18")
    assert "dn" not in msg or "k" in msg

def test_build_due_message_expenses():
    invoices = []
    expenses = [
        {"number": "NV-001", "supplier_name": "Dodavatel", "total": "5000",
         "currency": "CZK", "due_on": "2026-03-15", "remaining_amount": "5000",
         "status": "overdue"},
    ]
    msg = build_due_message(invoices, expenses, today="2026-03-18")
    assert "NV-001" in msg
    assert "NÁKLADY" in msg
    assert "zaplatit" in msg

def test_build_due_message_both():
    invoices = [
        {"number": "FV-001", "client_name": "Klient", "total": "10000",
         "currency": "CZK", "due_on": "2026-03-10", "remaining_amount": "10000",
         "status": "overdue"},
    ]
    expenses = [
        {"number": "NV-001", "supplier_name": "Dodavatel", "total": "3000",
         "currency": "CZK", "due_on": "2026-03-18", "remaining_amount": "3000",
         "status": "open"},
    ]
    msg = build_due_message(invoices, expenses, today="2026-03-18")
    assert "FAKTURY" in msg
    assert "NÁKLADY" in msg
    assert "FV-001" in msg
    assert "NV-001" in msg
