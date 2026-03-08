"""Number search, purchase, and management."""

from __future__ import annotations

from typing import Any

from plivo_agentstack._http import HttpTransport


class NumbersClient:
    """Phone number management — search, buy, manage, lookup.

    Usage::
        async with AsyncClient(auth_id, auth_token) as client:
            numbers = await client.numbers.search("US", type="local")
            await client.numbers.buy(number="+14155551234")
    """

    def __init__(self, http: HttpTransport) -> None:
        self._http = http
        self.lookup = LookupResource(http)

    async def list(
        self,
        *,
        type: str | None = None,
        number_startswith: str | None = None,
        subaccount: str | None = None,
        alias: str | None = None,
        services: str | None = None,
        limit: int = 20,
        offset: int = 0,
        **kwargs: Any,
    ) -> dict:
        """List owned phone numbers."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        for key, val in {
            "type": type,
            "number_startswith": number_startswith,
            "subaccount": subaccount,
            "alias": alias,
            "services": services,
        }.items():
            if val is not None:
                params[key] = val
        params.update(kwargs)
        return await self._http.request(
            "GET",
            f"/v1/Account/{self._http.auth_id}/Number/",
            params=params,
        )

    async def get(self, number: str) -> dict:
        """Get details for a specific phone number."""
        return await self._http.request(
            "GET",
            f"/v1/Account/{self._http.auth_id}/Number/{number}/",
        )

    async def buy(
        self,
        number: str,
        *,
        app_id: str | None = None,
        **kwargs: Any,
    ) -> dict:
        """Buy a phone number."""
        body: dict[str, Any] = {}
        if app_id:
            body["app_id"] = app_id
        body.update(kwargs)
        return await self._http.request(
            "POST",
            f"/v1/Account/{self._http.auth_id}/PhoneNumber/{number}/",
            json=body if body else None,
        )

    async def update(
        self,
        number: str,
        *,
        app_id: str | None = None,
        subaccount: str | None = None,
        alias: str | None = None,
        **kwargs: Any,
    ) -> dict:
        """Update phone number configuration."""
        body: dict[str, Any] = {}
        if app_id is not None:
            body["app_id"] = app_id
        if subaccount:
            body["subaccount"] = subaccount
        if alias:
            body["alias"] = alias
        body.update(kwargs)
        return await self._http.request(
            "POST",
            f"/v1/Account/{self._http.auth_id}/Number/{number}/",
            json=body,
        )

    async def delete(self, number: str) -> None:
        """Unrent a phone number."""
        await self._http.request(
            "DELETE",
            f"/v1/Account/{self._http.auth_id}/Number/{number}/",
        )

    async def search(
        self,
        country_iso: str,
        *,
        type: str | None = None,
        pattern: str | None = None,
        region: str | None = None,
        services: str | None = None,
        lata: int | None = None,
        rate_center: str | None = None,
        city: str | None = None,
        limit: int = 20,
        offset: int = 0,
        **kwargs: Any,
    ) -> dict:
        """Search available phone numbers."""
        params: dict[str, Any] = {
            "country_iso": country_iso,
            "limit": limit,
            "offset": offset,
        }
        for key, val in {
            "type": type,
            "pattern": pattern,
            "region": region,
            "services": services,
            "lata": lata,
            "rate_center": rate_center,
            "city": city,
        }.items():
            if val is not None:
                params[key] = val
        params.update(kwargs)
        return await self._http.request(
            "GET",
            f"/v1/Account/{self._http.auth_id}/PhoneNumber/",
            params=params,
        )


class LookupResource:
    """Number lookup (carrier information)."""

    def __init__(self, http: HttpTransport) -> None:
        self._http = http

    async def get(self, number: str, *, type: str = "carrier") -> dict:
        """Look up carrier information for a phone number."""
        return await self._http.request(
            "GET",
            f"/v1/Number/{number}",
            params={"type": type},
        )
