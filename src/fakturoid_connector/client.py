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
        params: dict[str, Any] = {"query": query}
        if tags:
            params["tags"] = tags
        return self._get_all("/invoices/search.json", params)

    def get_invoice(self, invoice_id: int) -> dict[str, Any]:
        return self._get(f"/invoices/{invoice_id}.json")

    def create_invoice(self, data: dict[str, Any]) -> dict[str, Any]:
        return self._post("/invoices.json", data)

    def update_invoice(self, invoice_id: int, data: dict[str, Any]) -> dict[str, Any]:
        return self._patch(f"/invoices/{invoice_id}.json", data)

    def download_invoice_pdf(self, invoice_id: int) -> bytes | None:
        self._ensure_token()
        resp = self._session.get(f"{self._base}/invoices/{invoice_id}/download.pdf")
        if resp.status_code == 204:
            return None
        resp.raise_for_status()
        return resp.content

    def fire_invoice(self, invoice_id: int, event: str) -> None:
        self._ensure_token()
        resp = self._session.post(
            f"{self._base}/invoices/{invoice_id}/fire.json",
            json={"event": event},
        )
        resp.raise_for_status()

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
