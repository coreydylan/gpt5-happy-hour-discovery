from __future__ import annotations

import re
from typing import Any, Dict, List

from .base import BaseConnector, ConnectorResponse

try:
    from openai import OpenAI  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None


DAY_NAMES = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "daily",
]

TIME_PATTERN = re.compile(r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b", re.IGNORECASE)


class StructuredExtractorConnector(BaseConnector):
    tool_id = "structured_llm_extractor"
    requires_credentials = ("OPENAI_API_KEY",)
    description = "Map free-form text into structured happy hour entries."

    def __init__(self, *, allow_mock: bool = True) -> None:
        super().__init__(allow_mock=allow_mock)
        self._client = OpenAI() if OpenAI is not None and self.has_credentials() else None

    def _invoke_live(
        self,
        *,
        content: str,
        schema_hint: Dict[str, Any] | None = None,
        **_: Any,
    ) -> ConnectorResponse:
        if self._client is not None:  # pragma: no cover - network code path
            prompt = (
                "Extract happy hour schedules and specials from the provided text. "
                "Return JSON with `hours` and `specials` arrays. Text:\n"
                f"{content[:6000]}"
            )
            try:
                response = self._client.responses.create(
                    model="gpt-4o-mini",
                    input=prompt,
                    response_format={"type": "json_object"},
                )
                structured = response.output[0].content[0].text  # type: ignore[index]
                return ConnectorResponse(
                    data={"raw": structured},
                    metadata={"source": "structured_llm_extractor", "mode": "live", "engine": "openai:gpt-4o-mini"},
                    warnings=[],
                )
            except Exception as exc:
                warning = f"LLM extraction failed: {exc}. Falling back to heuristics."
                heuristics = self._heuristic_extract(content)
                return ConnectorResponse(
                    data=heuristics,
                    metadata={"source": "structured_llm_extractor", "mode": "live", "engine": "heuristic"},
                    warnings=[warning],
                )

        heuristics = self._heuristic_extract(content)
        return ConnectorResponse(
            data=heuristics,
            metadata={"source": "structured_llm_extractor", "mode": "live", "engine": "heuristic"},
            warnings=[],
        )

    def _invoke_mock(self, *, content: str, **_: Any) -> ConnectorResponse:
        heuristics = self._heuristic_extract(content)
        return ConnectorResponse(
            data=heuristics,
            metadata={"source": "structured_llm_extractor", "mode": "mock", "engine": "heuristic"},
            warnings=[],
        )

    def _heuristic_extract(self, content: str) -> Dict[str, Any]:
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        hours: List[Dict[str, Any]] = []
        specials: List[Dict[str, Any]] = []

        for line in lines:
            lowered = line.lower()
            if any(day in lowered for day in DAY_NAMES) and TIME_PATTERN.search(lowered):
                hours.append({"text": line})
            if "$" in line or "off" in lowered:
                specials.append({"text": line})

        return {
            "hours": hours[:10],
            "specials": specials[:10],
            "raw_line_count": len(lines),
        }
