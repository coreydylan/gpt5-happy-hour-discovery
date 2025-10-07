from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional

from .base import BaseConnector, ConnectorResponse, sanitize_query
from .http_client import get_json

GOOGLE_PLACES_URL = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"


class GooglePlacesConnector(BaseConnector):
    tool_id = "google_places_search"
    requires_credentials = ("GOOGLE_PLACES_API_KEY",)
    description = "Lookup businesses using the Google Places API."

    def __init__(self, *, allow_mock: bool = True) -> None:
        super().__init__(allow_mock=allow_mock)

    def _invoke_live(
        self,
        *,
        query: str,
        location_bias: Optional[str] = None,
        fields: str = "place_id,name,formatted_address,geometry,types,website",
        **_: Any,
    ) -> ConnectorResponse:
        params: Dict[str, Any] = {
            "input": query,
            "inputtype": "textquery",
            "fields": fields,
            "key": self._google_api_key,
        }
        if location_bias:
            params["locationbias"] = location_bias

        payload = get_json(GOOGLE_PLACES_URL, params=params)
        candidates = [
            {
                "place_id": candidate.get("place_id"),
                "name": candidate.get("name"),
                "formatted_address": candidate.get("formatted_address"),
                "types": candidate.get("types") or [],
                "geometry": candidate.get("geometry"),
                "website": candidate.get("website"),
            }
            for candidate in payload.get("candidates", [])
        ]

        warnings = []
        status = payload.get("status")
        if status not in {"OK", "ZERO_RESULTS"}:
            warnings.append(f"Google Places returned status {status}")

        return ConnectorResponse(
            data={"candidates": candidates, "raw": payload},
            metadata={"source": "google_places", "status": status, "mode": "live"},
            warnings=warnings,
        )

    def _invoke_mock(self, *, query: str, **_: Any) -> ConnectorResponse:
        normalized = sanitize_query(query)
        mock_id = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]
        display_name = normalized.title() if normalized else "Unknown Venue"
        return ConnectorResponse(
            data={
                "candidates": [
                    {
                        "place_id": f"mock-{mock_id}",
                        "name": display_name,
                        "formatted_address": "123 Mockingbird Lane",
                        "types": ["mock"],
                        "geometry": {"location": {"lat": 0.0, "lng": 0.0}},
                        "website": "https://example.com/mock",
                    }
                ],
                "raw": {"mode": "mock"},
            },
            metadata={"source": "google_places", "mode": "mock"},
            warnings=[],
        )

    @property
    def _google_api_key(self) -> str:
        from os import getenv

        value = getenv("GOOGLE_PLACES_API_KEY")
        if not value:
            raise RuntimeError("Expected GOOGLE_PLACES_API_KEY to be set")
        return value
