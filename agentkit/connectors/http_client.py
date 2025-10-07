from __future__ import annotations

import json
from typing import Any, Dict, Optional

from .base import ConnectorError

try:
    import httpx
except ImportError:  # pragma: no cover - only hit in lightweight envs
    httpx = None


class HttpRequestError(ConnectorError):
    """Raised when an HTTP request fails."""


def _encode_params(params: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if params is None:
        return None
    # convert any non-string values to string to avoid http clients choking
    return {key: str(value) for key, value in params.items()}


def get_text(
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 15.0,
) -> str:
    """Fetch raw text from an HTTP endpoint."""
    if httpx is not None:
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                response = client.get(url, params=_encode_params(params), headers=headers)
                response.raise_for_status()
                return response.text
        except Exception as exc:  # pragma: no cover - surface descriptive error
            raise HttpRequestError(str(exc)) from exc

    # Fallback to urllib so we do not depend on httpx being installed
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    if params:
        url = f"{url}?{urlencode(_encode_params(params))}"
    request = Request(url, headers=headers or {})
    try:
        with urlopen(request, timeout=timeout) as response:  # type: ignore[arg-type]
            return response.read().decode("utf-8")
    except Exception as exc:  # pragma: no cover - fallback path
        raise HttpRequestError(str(exc)) from exc


def get_json(
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 15.0,
) -> Dict[str, Any]:
    payload = get_text(url, params=params, headers=headers, timeout=timeout)
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:  # pragma: no cover - unexpected server payload
        raise HttpRequestError(f"Failed to decode JSON from {url}: {exc}") from exc
