from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List

from .base import BaseConnector, ConnectorResponse, sanitize_query

try:
    from openai import OpenAI  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None


DEFAULT_KEYWORDS = [
    "happy hour",
    "drink special",
    "draft beer",
    "wine",
    "cocktail",
    "margarita",
    "discount",
    "appetizer",
    "half off",
]


class SemanticScanConnector(BaseConnector):
    tool_id = "semantic_scan"
    requires_credentials = ("OPENAI_API_KEY",)
    description = "Summarise snippets and highlight happy hour signals."

    def __init__(
        self,
        *,
        allow_mock: bool = True,
        keywords: Iterable[str] = DEFAULT_KEYWORDS,
    ) -> None:
        super().__init__(allow_mock=allow_mock)
        self.keywords = [sanitize_query(keyword.lower()) for keyword in keywords]
        self._client = OpenAI() if OpenAI is not None and self.has_credentials() else None

    def _invoke_live(
        self,
        *,
        content: str,
        focus: str = "happy hour deals",
        top_k: int = 5,
        **_: Any,
    ) -> ConnectorResponse:
        summary: str
        highlights: List[Dict[str, Any]]
        engine = "heuristic"

        if self._client is not None:  # pragma: no cover - network path is not exercised in tests
            prompt = (
                "You are assisting a happy hour discovery agent. "
                "Highlight excerpts that confirm happy hour availability, discounts, or schedules. "
                f"Focus: {focus}\n\nText:\n{content[:4000]}"
            )
            try:
                response = self._client.responses.create(
                    model="gpt-4o-mini",
                    input=prompt,
                )
                summary = response.output_text.strip()
                highlights = [{"summary": summary, "confidence": 0.6}]
                engine = "openai:gpt-4o-mini"
            except Exception as exc:
                summary = f"LLM request failed: {exc}. Falling back to keyword scan."
                highlights = []
        else:
            summary = ""
            highlights = []

        if not highlights:
            highlights = self._keyword_scan(content, top_k=top_k)
            if not summary:
                summary = "Keyword heuristic scan completed."

        confidence = self._confidence_from_highlights(highlights)

        return ConnectorResponse(
            data={
                "summary": summary,
                "highlights": highlights,
                "confidence": confidence,
            },
            metadata={"source": "semantic_scan", "mode": "live", "engine": engine},
            warnings=[],
        )

    def _invoke_mock(self, *, content: str, **_: Any) -> ConnectorResponse:
        highlights = self._keyword_scan(content, top_k=3)
        return ConnectorResponse(
            data={
                "summary": "Semantic scan mock executed. No credentials available.",
                "highlights": highlights,
                "confidence": self._confidence_from_highlights(highlights),
            },
            metadata={"source": "semantic_scan", "mode": "mock"},
            warnings=[],
        )

    # ------------------------------------------------------------------ #
    # Helper methods
    # ------------------------------------------------------------------ #
    def _keyword_scan(self, content: str, *, top_k: int) -> List[Dict[str, Any]]:
        lowered = content.lower()
        matches = []
        for keyword in self.keywords:
            count = lowered.count(keyword)
            if count:
                matches.append({"keyword": keyword, "count": count})
        matches.sort(key=lambda item: item["count"], reverse=True)
        return matches[:top_k]

    def _confidence_from_highlights(self, highlights: List[Dict[str, Any]]) -> float:
        if not highlights:
            return 0.0
        max_count = max(item["count"] for item in highlights)
        confidence = 1 - math.exp(-max_count)
        return round(confidence, 3)
