"""E2E API tests using HTTPX + FastAPI TestClient."""

from __future__ import annotations

import pytest


class TestHealthEndpoints:
    async def test_liveness(self, client, auth_headers) -> None:
        response = await client.get("/api/v1/health/live")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestAuthEndpoints:
    async def test_login_success(self, client, api_user) -> None:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client) -> None:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    async def test_login_unknown_email(self, client) -> None:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "password123"},
        )
        assert response.status_code == 401

    async def test_me_returns_user(self, client, auth_headers) -> None:
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["role"] == "admin"

    async def test_me_unauthenticated(self, client) -> None:
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 403

    async def test_refresh_token(self, client) -> None:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        refresh_token = login.json()["refresh_token"]
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_refresh_with_access_token_fails(self, client, access_token) -> None:
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert response.status_code == 401


class TestProviderAccountEndpoints:
    async def test_register_provider_account(self, client, auth_headers) -> None:
        response = await client.post(
            "/api/v1/provider-accounts/",
            headers=auth_headers,
            json={
                "provider_type": "STUB",
                "account_name": "test-stub",
                "credentials_json": {"webhook_secret": "secret"},
                "priority": 100,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["provider_type"] == "STUB"
        assert data["account_name"] == "test-stub"
        assert data["is_active"] is True

    async def test_list_provider_accounts(self, client, auth_headers) -> None:
        # Register one first
        await client.post(
            "/api/v1/provider-accounts/",
            headers=auth_headers,
            json={
                "provider_type": "STUB",
                "account_name": "test-stub-list",
                "credentials_json": {},
            },
        )
        response = await client.get("/api/v1/provider-accounts/", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_get_provider_account(self, client, auth_headers) -> None:
        create = await client.post(
            "/api/v1/provider-accounts/",
            headers=auth_headers,
            json={
                "provider_type": "STUB",
                "account_name": "test-get",
                "credentials_json": {},
            },
        )
        account_id = create.json()["id"]
        response = await client.get(
            f"/api/v1/provider-accounts/{account_id}", headers=auth_headers
        )
        assert response.status_code == 200

    async def test_activate_deactivate(self, client, auth_headers) -> None:
        create = await client.post(
            "/api/v1/provider-accounts/",
            headers=auth_headers,
            json={
                "provider_type": "STUB",
                "account_name": "test-toggle",
                "credentials_json": {},
            },
        )
        account_id = create.json()["id"]
        deactivate = await client.post(
            f"/api/v1/provider-accounts/{account_id}/deactivate", headers=auth_headers
        )
        assert deactivate.status_code == 200
        assert deactivate.json()["is_active"] is False

        activate = await client.post(
            f"/api/v1/provider-accounts/{account_id}/activate", headers=auth_headers
        )
        assert activate.status_code == 200
        assert activate.json()["is_active"] is True

    async def test_register_requires_auth(self, client) -> None:
        response = await client.post(
            "/api/v1/provider-accounts/",
            json={"provider_type": "STUB", "account_name": "x", "credentials_json": {}},
        )
        assert response.status_code == 403


class TestDocumentEndpoints:
    async def _create_account(self, client, auth_headers) -> str:
        resp = await client.post(
            "/api/v1/provider-accounts/",
            headers=auth_headers,
            json={
                "provider_type": "STUB",
                "account_name": f"doc-test-account",
                "credentials_json": {},
            },
        )
        return resp.json()["id"]

    async def test_list_documents_empty(self, client, auth_headers) -> None:
        response = await client.get("/api/v1/documents/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    async def test_get_document_not_found(self, client, auth_headers) -> None:
        import uuid
        response = await client.get(
            f"/api/v1/documents/{uuid.uuid4()}", headers=auth_headers
        )
        assert response.status_code == 404


class TestDLQEndpoints:
    async def test_list_dlq_empty(self, client, auth_headers) -> None:
        response = await client.get("/api/v1/dlq/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    async def test_get_dlq_entry_not_found(self, client, auth_headers) -> None:
        import uuid
        response = await client.get(
            f"/api/v1/dlq/{uuid.uuid4()}", headers=auth_headers
        )
        assert response.status_code == 404


class TestSecurityHeaders:
    async def test_security_headers_present(self, client, auth_headers) -> None:
        response = await client.get("/api/v1/health/live")
        assert "x-content-type-options" in response.headers
        assert "x-frame-options" in response.headers
        assert response.headers["x-frame-options"] == "DENY"

    async def test_request_id_header(self, client) -> None:
        response = await client.get("/api/v1/health/live")
        assert "x-request-id" in response.headers
