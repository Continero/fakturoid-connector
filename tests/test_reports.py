from fakturoid_connector.reports import monthly_report, yearly_report

def test_monthly_report():
    invoices = [
        {"number": "FV-001", "client_name": "A", "total": "1000",
         "currency": "CZK", "issued_on": "2026-03-01", "status": "paid"},
        {"number": "FV-002", "client_name": "B", "total": "2000",
         "currency": "CZK", "issued_on": "2026-03-15", "status": "open"},
        {"number": "FV-003", "client_name": "C", "total": "500",
         "currency": "CZK", "issued_on": "2026-02-01", "status": "paid"},
    ]
    report = monthly_report(invoices, 2026, 3)
    assert "2026-03" in report
    assert "FV-001" in report
    assert "FV-002" in report
    assert "FV-003" not in report

def test_yearly_report():
    invoices = [
        {"number": "FV-001", "total": "1000", "issued_on": "2026-01-01", "status": "paid"},
        {"number": "FV-002", "total": "2000", "issued_on": "2026-03-01", "status": "open"},
    ]
    report = yearly_report(invoices, 2026)
    assert "2026" in report
    assert "3,000" in report
