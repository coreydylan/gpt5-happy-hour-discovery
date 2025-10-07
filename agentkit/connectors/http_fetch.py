from __future__ import annotations

from typing import Any, Dict, Optional

from .base import BaseConnector, ConnectorResponse
from .http_client import get_text, HttpRequestError


class HttpFetchConnector(BaseConnector):
    tool_id = "http_fetch"
    description = "Lightweight HTTP GET helper used by evaluators."

    def __init__(self, *, allow_mock: bool = True) -> None:
        # allow_mock is ignored here but kept for parity with other connectors
        super().__init__(allow_mock=allow_mock)

    def _invoke_live(
        self,
        *,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 15.0,
        **_: Any,
    ) -> ConnectorResponse:
        try:
            body = get_text(url, headers=headers, timeout=timeout)
            return ConnectorResponse(
                data={"url": url, "body": body},
                metadata={"source": "http_fetch", "mode": "live"},
                warnings=[],
            )
        except HttpRequestError as exc:
            # Propagate an empty payload with descriptive warnings so the agent can decide.
            return ConnectorResponse(
                data={"url": url, "body": ""},
                metadata={"source": "http_fetch", "mode": "live"},
                warnings=[f"http_fetch failed for {url}: {exc}"],
            )

    def _invoke_mock(self, *, url: str, **_: Any) -> ConnectorResponse:
        # http_fetch does not depend on credentials, so fallback mirrors live.
        return ConnectorResponse(
            data={"url": url, "body": "<mock-http-response>"},
            metadata={"source": "http_fetch", "mode": "mock"},
            warnings=["http_fetch returned mock payload to avoid external HTTP calls."],
        )
