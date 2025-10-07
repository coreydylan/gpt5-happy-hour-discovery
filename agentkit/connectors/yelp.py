from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional

from .base import BaseConnector, ConnectorResponse, sanitize_query
from .http_client import get_json

YELP_SEARCH_URL = "https://api.yelp.com/v3/businesses/search"


class YelpBusinessConnector(BaseConnector):
    tool_id = "yelp_business_lookup"
    requires_credentials = ("YELP_API_KEY",)
    description = "Retrieve businesses from Yelp Fusion search."

    def __init__(self, *, allow_mock: bool = True) -> None:
        super().__init__(allow_mock=allow_mock)

    def _invoke_live(
        self,
        *,
        query: str,
        location: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        limit: int = 5,
        **_: Any,
    ) -> ConnectorResponse:
        params: Dict[str, Any] = {"term": query, "limit": limit}
        if location:
            params["location"] = location
        if latitude is not None and longitude is not None:
            params["latitude"] = latitude
            params["longitude"] = longitude

        payload = get_json(
            YELP_SEARCH_URL,
            params=params,
            headers={"Authorization": f"Bearer {self._api_key}"},
        )

        businesses = [
            {
                "id": business.get("id"),
                "name": business.get("name"),
                "url": business.get("url"),
                "rating": business.get("rating"),
                "review_count": business.get("review_count"),
                "location": business.get("location"),
                "categories": business.get("categories"),
                "coordinates": business.get("coordinates"),
            }
            for business in payload.get("businesses", [])
        ]

        warnings = []
        if payload.get("businesses") is None:
            warnings.append("Yelp response missing 'businesses'")

        return ConnectorResponse(
            data={"businesses": businesses, "raw": payload},
            metadata={"source": "yelp", "mode": "live"},
            warnings=warnings,
        )

    def _invoke_mock(self, *, query: str, location: Optional[str] = None, **_: Any) -> ConnectorResponse:
        normalized = sanitize_query(query)
        location_display = location or "Mock City"
        digest = hashlib.md5((normalized + location_display).encode("utf-8")).hexdigest()[:10]
        return ConnectorResponse(
            data={
                "businesses": [
                    {
                        "id": f"mock-{digest}",
                        "name": normalized or "Unknown Venue",
                        "url": "https://example.com/mock-yelp",
                        "rating": 4.2,
                        "review_count": 123,
                        "location": {"address1": "1 Test Street", "city": location_display},
                        "categories": [{"title": "Mock Category"}],
                        "coordinates": {"latitude": 0.0, "longitude": 0.0},
                    }
                ],
                "raw": {"mode": "mock"},
            },
            metadata={"source": "yelp", "mode": "mock"},
            warnings=[],
        )

    @property
    def _api_key(self) -> str:
        from os import getenv

        value = getenv("YELP_API_KEY")
        if not value:
            raise RuntimeError("Expected YELP_API_KEY to be set")
        return value
