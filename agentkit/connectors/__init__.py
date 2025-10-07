"""
Connector registry for AgentKit tool IDs defined in the workflow YAML.

Each entry exposes a callable object that returns a `ConnectorResponse`
structure when invoked. Connectors degrade gracefully when environment
credentials are missing so local development is possible without live API keys.
"""

from __future__ import annotations

from typing import Callable, Dict

from .base import BaseConnector, ConnectorResponse, ConnectorCredentialsError, ConnectorError
from .browser_openai import OpenAIBrowserConnector
from .google_places import GooglePlacesConnector
from .http_fetch import HttpFetchConnector
from .search import WebSearchConnector
from .semantic_scan import SemanticScanConnector
from .structured_extractor import StructuredExtractorConnector
from .yelp import YelpBusinessConnector

ConnectorFactory = Callable[..., BaseConnector]

_FACTORIES: Dict[str, ConnectorFactory] = {
    GooglePlacesConnector.tool_id: GooglePlacesConnector,
    YelpBusinessConnector.tool_id: YelpBusinessConnector,
    WebSearchConnector.tool_id: WebSearchConnector,
    HttpFetchConnector.tool_id: HttpFetchConnector,
    SemanticScanConnector.tool_id: SemanticScanConnector,
    OpenAIBrowserConnector.tool_id: OpenAIBrowserConnector,
    StructuredExtractorConnector.tool_id: StructuredExtractorConnector,
}


def build_registry(*, allow_mock: bool = True) -> Dict[str, BaseConnector]:
    """Instantiate all connector implementations."""
    return {tool_id: factory(allow_mock=allow_mock) for tool_id, factory in _FACTORIES.items()}


# Default registry used by consumers that just need the mapping
connectors: Dict[str, BaseConnector] = build_registry()

__all__ = [
    "connectors",
    "build_registry",
    "ConnectorResponse",
    "ConnectorError",
    "ConnectorCredentialsError",
]
