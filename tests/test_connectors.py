import os
import unittest

from agentkit.connectors import build_registry
from agentkit.connectors.google_places import GooglePlacesConnector
from agentkit.connectors.yelp import YelpBusinessConnector
from agentkit.connectors.search import WebSearchConnector
from agentkit.connectors.semantic_scan import SemanticScanConnector
from agentkit.connectors.structured_extractor import StructuredExtractorConnector
from agentkit.connectors.http_fetch import HttpFetchConnector
from agentkit.connectors.browser_openai import OpenAIBrowserConnector


def _clear_env(var: str) -> None:
    os.environ.pop(var, None)


class ConnectorTests(unittest.TestCase):
    def setUp(self) -> None:
        # ensure we run in mock-friendly mode
        for var in ("GOOGLE_PLACES_API_KEY", "YELP_API_KEY", "SERP_API_KEY", "OPENAI_API_KEY"):
            _clear_env(var)

    def test_google_places_mock(self) -> None:
        connector = GooglePlacesConnector()
        response = connector(query="Test Venue", location_bias="point:0,0")
        self.assertEqual(response.metadata["mode"], "mock")
        self.assertTrue(response.data["candidates"])

    def test_yelp_mock(self) -> None:
        connector = YelpBusinessConnector()
        response = connector(query="Test Venue", location="Nowhere")
        self.assertEqual(response.metadata["mode"], "mock")
        self.assertTrue(response.data["businesses"])

    def test_search_mock(self) -> None:
        connector = WebSearchConnector()
        response = connector(query="test query", num=2)
        self.assertEqual(response.metadata["mode"], "mock")
        self.assertEqual(len(response.data["results"]), 2)

    def test_semantic_scan_keywords(self) -> None:
        connector = SemanticScanConnector()
        content = "Happy hour daily 3pm-6pm with half off appetizers."
        response = connector(content=content)
        self.assertGreater(response.data["confidence"], 0)
        self.assertEqual(response.metadata["mode"], "mock")

    def test_structured_extractor(self) -> None:
        connector = StructuredExtractorConnector()
        content = "Monday to Friday 4pm-6pm: $5 beers and half-price wings."
        response = connector(content=content)
        self.assertTrue(response.data["hours"])
        self.assertTrue(response.data["specials"])
        self.assertIn(response.metadata["mode"], {"live", "mock"})

    def test_http_fetch_fallback(self) -> None:
        connector = HttpFetchConnector()
        response = connector(url="https://invalid.localhost")
        # live mode attempted but should not raise; warnings should mention failure
        self.assertEqual(response.metadata["source"], "http_fetch")
        self.assertIsInstance(response.data["body"], str)
        self.assertTrue(response.warnings)

    def test_openai_browser_mock(self) -> None:
        connector = OpenAIBrowserConnector()
        response = connector(url="https://example.com")
        self.assertEqual(response.metadata["mode"], "mock")
        self.assertIn("summary", response.data)

    def test_build_registry_contains_tools(self) -> None:
        registry = build_registry()
        for tool_id in [
            "google_places_search",
            "yelp_business_lookup",
            "search_web",
            "http_fetch",
            "semantic_scan",
            "browser_headless",
            "structured_llm_extractor",
        ]:
            self.assertIn(tool_id, registry)


if __name__ == "__main__":
    unittest.main()
