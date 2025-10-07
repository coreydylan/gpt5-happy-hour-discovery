from __future__ import annotations

from typing import Any, Dict, List

from .base import BaseConnector, ConnectorResponse

try:
    from openai import OpenAI  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None


class OpenAIBrowserConnector(BaseConnector):
    """
    Connector that delegates page retrieval to OpenAI's hosted browser tool.

    When `OPENAI_API_KEY` is configured and the `openai` package is available,
    the connector issues a `responses.create` call with the browser tool enabled.
    In local environments without network access, we fall back to a deterministic
    mock payload so downstream agents continue to operate.
    """

    tool_id = "browser_headless"
    requires_credentials = ("OPENAI_API_KEY",)
    description = "Leverage OpenAI's browser tool to fetch and summarise pages."

    def __init__(self, *, allow_mock: bool = True, model: str = "gpt-4.1-mini") -> None:
        super().__init__(allow_mock=allow_mock)
        self.model = model

    def _invoke_live(
        self,
        *,
        url: str,
        instructions: str = "Capture the main text content and note any happy hour details.",
        **_: Any,
    ) -> ConnectorResponse:
        if OpenAI is None:  # pragma: no cover - dependency missing
            # Degenerate to mock behaviour with warning.
            payload = self._invoke_mock(url=url)
            payload.metadata["mode"] = "mock"
            payload.warnings.append("openai package is not installed; using mock browser response.")
            return payload

        client = OpenAI()
        try:  # pragma: no cover - network path is not exercised in tests
            response = client.responses.create(
                model=self.model,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"{instructions}\nURL: {url}"},
                        ],
                    }
                ],
                tools=[{"type": "browser"}],
            )
            summary, captures = self._extract_browser_output(response)
            return ConnectorResponse(
                data={
                    "url": url,
                    "summary": summary,
                    "captures": captures,
                    "raw": response.model_dump() if hasattr(response, "model_dump") else None,
                },
                metadata={"source": "browser_headless", "mode": "live", "engine": self.model},
                warnings=[],
            )
        except Exception as exc:
            fallback = self._invoke_mock(url=url)
            fallback.metadata["mode"] = "mock"
            fallback.warnings.append(f"OpenAI browser request failed: {exc}")
            return fallback

    def _invoke_mock(self, *, url: str, **_: Any) -> ConnectorResponse:
        return ConnectorResponse(
            data={
                "url": url,
                "summary": "Browser mock executed. Configure OPENAI_API_KEY for live capture.",
                "captures": [],
            },
            metadata={"source": "browser_headless", "mode": "mock", "engine": "heuristic"},
            warnings=[],
        )

    # ------------------------------------------------------------------ #
    # Helper methods
    # ------------------------------------------------------------------ #
    def _extract_browser_output(self, response: Any) -> tuple[str, List[Dict[str, Any]]]:
        """
        Attempt to extract summary text and any captured artifacts from the
        responses API payload. The shape depends on server behaviour, so the
        parser is defensive and collapses everything to strings.
        """
        summary_parts: List[str] = []
        captures: List[Dict[str, Any]] = []

        output = getattr(response, "output", None)
        if not output:
            return ("", captures)

        for item in output:
            content = getattr(item, "content", None)
            if not content:
                continue
            for block in content:
                block_type = block.get("type")
                if block_type == "text":
                    text = block.get("text", "")
                    if text:
                        summary_parts.append(text)
                elif block_type == "tool_call":
                    captures.append(block)

        return ("\n".join(summary_parts).strip(), captures)
