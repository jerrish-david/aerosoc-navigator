"""Supabase HTTP boundary. Every database request uses the student's JWT and RLS."""

from typing import Any

import httpx

from app.institute.config import PortalSettings


class SupabaseFailure(Exception):
    def __init__(self, status: int) -> None:
        self.status = status


class SupabaseGateway:
    def __init__(self, settings: PortalSettings) -> None:
        self.settings = settings

    async def request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        data: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> Any:
        headers = {"apikey": self.settings.supabase_publishable_key}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if path.startswith("/rest/"):
            headers["Accept-Profile"] = "institute"
        try:
            async with httpx.AsyncClient(timeout=12, follow_redirects=False) as client:
                response = await client.request(
                    method,
                    self.settings.supabase_url.rstrip("/") + path,
                    headers=headers,
                    json=data,
                    params=params,
                )
        except httpx.RequestError:
            raise SupabaseFailure(503) from None
        if response.is_error:
            raise SupabaseFailure(response.status_code)
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            raise SupabaseFailure(502) from None

    async def send_link(self, email: str, redirect: str) -> None:
        await self.request(
            "POST",
            "/auth/v1/otp",
            params={"redirect_to": redirect},
            data={"email": email, "create_user": False},
        )

    async def verify(self, token_hash: str) -> dict[str, Any]:
        result: dict[str, Any] = await self.request(
            "POST", "/auth/v1/verify", data={"token_hash": token_hash, "type": "email"}
        )
        return result

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        result: dict[str, Any] = await self.request(
            "POST",
            "/auth/v1/token",
            params={"grant_type": "refresh_token"},
            data={"refresh_token": refresh_token},
        )
        return result

    async def user(self, token: str) -> dict[str, Any]:
        result: dict[str, Any] = await self.request("GET", "/auth/v1/user", token=token)
        return result

    async def logout(self, token: str) -> None:
        await self.request("POST", "/auth/v1/logout", token=token, params={"scope": "local"})

    async def rows(self, table: str, token: str, **query: str) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = await self.request(
            "GET", f"/rest/v1/{table}", token=token, params=query
        )
        return result
