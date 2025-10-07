from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional

from .base import BaseConnector, ConnectorResponse, sanitize_query
from .http_client import get_json, HttpRequestError

SERP_API_URL = "https://serpapi.com/search.json"


class WebSearchConnector(BaseConnector):
    tool_id = "search_web"
    requires_credentials = ("SERP_API_KEY",)
    description = "Perform web search via SerpAPI."

    def __init__(self, *, allow_mock: bool = True, default_engine: str = "google") -> None:
        super().__init__(allow_mock=allow_mock)
        self.default_engine = default_engine

    def _invoke_live(
        self,
        *,
        query: str,
        engine: Optional[str] = None,
        num: int = 5,
        **_: Any,
    ) -> ConnectorResponse:
        params: Dict[str, Any] = {
            "q": query,
            "api_key": self._api_key,
            "engine": engine or self.default_engine,
            "num": num,
        }
        try:
            payload = get_json(SERP_API_URL, params=params)
        except HttpRequestError as exc:
            # Surface a structured response so the orchestrator can decide what to do next.
            return ConnectorResponse(
                data={"results": []},
                metadata={"source": "serpapi", "mode": "live"},
                warnings=[f"search_web request failed: {exc}"],
            )

        organic = payload.get("organic_results") or []
        results = [
            {
                "title": item.get("title"),
                "link": item.get("link"),
                "snippet": item.get("snippet"),
                "position": item.get("position"),
            }
            for item in organic[:num]
        ]

        return ConnectorResponse(
            data={"results": results, "raw": payload},
            metadata={"source": "serpapi", "mode": "live"},
            warnings=[],
        )

    def _invoke_mock(self, *, query: str, num: int = 5, **_: Any) -> ConnectorResponse:
        normalized = sanitize_query(query)
        base_hash = hashlib.sha1(normalized.encode("utf-8")).hexdigest()
        results = []
        for idx in range(min(num, 5)):
            digest = base_hash[idx : idx + 8]
            results.append(
                {
                    "title": f"Mock result {idx + 1} for {normalized}",
                    "link": f"https://example.com/{digest}",
                    "snippet": "Mock response generated because SERP_API_KEY is not configured.",
                    "position": idx + 1,
                }
            )
        return ConnectorResponse(
            data={"results": results, "raw": {"mode": "mock"}},
            metadata={"source": "serpapi", "mode": "mock"},
            warnings=[],
        )

    @property
    def _api_key(self) -> str:
        from os import getenv

        value = getenv("SERP_API_KEY")
        if not value:
            raise RuntimeError("Expected SERP_API_KEY to be set")
        return value
