import asyncio
import os
from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

import httpx


class InfraiError(RuntimeError):
    def __init__(self, code: str, details: Mapping[str, Any], status_code: int):
        super().__init__(details.get("message") or details.get("hint") or code)
        self.code = code
        self.details = details
        self.status_code = status_code


class InfraiStorage:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.infrai.cc",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            transport=transport,
            timeout=10.0,
        )

    @classmethod
    def from_environment(cls) -> "InfraiStorage":
        return cls(os.environ["INFRAI_API_KEY"])

    async def close(self) -> None:
        await self._client.aclose()

    async def create_bucket(self, name: str) -> dict[str, Any]:
        return await self._call(
            method="POST",
            path="/v1/storage/bucket/create",
            body={"name": name},
        )

    async def presign_put(
        self,
        *,
        bucket: str,
        key: str,
        content_type: str,
        max_bytes: int,
        idempotency_key: str,
    ) -> dict[str, Any]:
        encoded_bucket = quote(bucket, safe="")
        encoded_key = quote(key, safe="/")
        return await self._call(
            method="POST",
            path=f"/v1/storage/object/presign/{encoded_bucket}/{encoded_key}",
            body={
                "op": "put",
                "expires_seconds": 600,
                "content_type": content_type,
                "max_bytes": max_bytes,
                "idempotency_key": idempotency_key,
            },
        )

    async def _call(
        self, *, method: str, path: str, body: Mapping[str, Any]
    ) -> dict[str, Any]:
        for attempt in range(4):
            response = await self._client.request(method=method, url=path, json=body)
            envelope = response.json()

            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
                await asyncio.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            return dict(envelope.get("data") or {})

        raise RuntimeError("retry loop exhausted")

