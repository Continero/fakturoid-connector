"""Tests for FakturoidClient."""

from unittest.mock import MagicMock, patch

import pytest

from fakturoid_connector.client import FakturoidClient, API_BASE


def _mock_token_response():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "access_token": "test_token_123",
        "token_type": "Bearer",
        "expires_in": 7200,
    }
    return resp


def _make_client(session):
    """Create a FakturoidClient with a pre-configured mock session."""
    session.post.return_value = _mock_token_response()
    return FakturoidClient(client_id="id", client_secret="secret", slug="test-slug")


@patch("fakturoid_connector.client.requests.Session")
def test_authenticate_sets_bearer_token(mock_session_cls):
    session = MagicMock()
    mock_session_cls.return_value = session
    session.post.return_value = _mock_token_response()

    client = FakturoidClient(client_id="id", client_secret="secret", slug="test-slug")

    session.post.assert_called_once()
    # Verify the token endpoint was called
    call_args = session.post.call_args
    assert call_args[0][0] == f"{API_BASE}/oauth/token"
    # Verify bearer token was set in session headers
    session.headers.update.assert_any_call({"Authorization": "Bearer test_token_123"})


@patch("fakturoid_connector.client.requests.Session")
def test_list_invoices(mock_session_cls):
    session = MagicMock()
    mock_session_cls.return_value = session
    client = _make_client(session)

    # Mock GET response with fewer than 40 items (single page)
    get_resp = MagicMock()
    get_resp.json.return_value = [{"id": 1}, {"id": 2}]
    session.get.return_value = get_resp

    result = client.list_invoices()

    session.get.assert_called_once()
    call_args = session.get.call_args
    assert "/invoices.json" in call_args[0][0]
    assert result == [{"id": 1}, {"id": 2}]


@patch("fakturoid_connector.client.requests.Session")
def test_list_invoices_with_status(mock_session_cls):
    session = MagicMock()
    mock_session_cls.return_value = session
    client = _make_client(session)

    get_resp = MagicMock()
    get_resp.json.return_value = [{"id": 1}]
    session.get.return_value = get_resp

    client.list_invoices(status="open")

    call_args = session.get.call_args
    assert call_args[1]["params"]["status"] == "open"


@patch("fakturoid_connector.client.requests.Session")
def test_search_invoices(mock_session_cls):
    session = MagicMock()
    mock_session_cls.return_value = session
    client = _make_client(session)

    get_resp = MagicMock()
    get_resp.json.return_value = [{"id": 10}]
    session.get.return_value = get_resp

    result = client.search_invoices("test query")

    call_args = session.get.call_args
    assert "/invoices/search.json" in call_args[0][0]
    assert call_args[1]["params"]["query"] == "test query"
    assert result == [{"id": 10}]


@patch("fakturoid_connector.client.requests.Session")
def test_get_invoice(mock_session_cls):
    session = MagicMock()
    mock_session_cls.return_value = session
    client = _make_client(session)

    get_resp = MagicMock()
    get_resp.json.return_value = {"id": 42, "number": "2024-001"}
    session.get.return_value = get_resp

    result = client.get_invoice(42)

    call_args = session.get.call_args
    assert "/invoices/42.json" in call_args[0][0]
    assert result["id"] == 42


@patch("fakturoid_connector.client.requests.Session")
def test_list_subjects(mock_session_cls):
    session = MagicMock()
    mock_session_cls.return_value = session
    client = _make_client(session)

    get_resp = MagicMock()
    get_resp.json.return_value = [{"id": 1, "name": "Acme"}]
    session.get.return_value = get_resp

    result = client.list_subjects()

    call_args = session.get.call_args
    assert "/subjects.json" in call_args[0][0]
    assert result == [{"id": 1, "name": "Acme"}]


@patch("fakturoid_connector.client.requests.Session")
def test_get_account(mock_session_cls):
    session = MagicMock()
    mock_session_cls.return_value = session
    client = _make_client(session)

    get_resp = MagicMock()
    get_resp.json.return_value = {"subdomain": "test-slug", "plan": "premium"}
    session.get.return_value = get_resp

    result = client.get_account()

    call_args = session.get.call_args
    assert "/account.json" in call_args[0][0]
    assert result["subdomain"] == "test-slug"
