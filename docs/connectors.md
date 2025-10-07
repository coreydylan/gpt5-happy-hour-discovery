# Connector Implementations

This repository now ships a reusable connector layer that maps the tool IDs
referenced in `agentkit/builder/happy_hour_agents.yaml` to concrete
implementations. The connectors live under `agentkit/connectors/` and share a
common interface that provides:

- **Credential-aware execution** – Live API calls happen only when the required
  environment variables are present.
- **Friendly fallbacks** – In local development (or CI) without external
  credentials the connectors return deterministic mock payloads and surface
  descriptive warnings instead of raising exceptions.
- **Structured responses** – Every connector returns a `ConnectorResponse`
  object containing the harvested data, metadata (mode, engine, rate limit
  notes), and warning messages that can be logged by the workflow runner.

## Tool → Connector Mapping

| Tool ID                    | Connector Class                          | Notes |
|----------------------------|------------------------------------------|-------|
| `google_places_search`     | `GooglePlacesConnector`                  | Calls the Google Places *Find Place* endpoint. |
| `yelp_business_lookup`     | `YelpBusinessConnector`                  | Uses Yelp Fusion search to retrieve businesses. |
| `search_web`               | `WebSearchConnector`                     | Integrates with SerpAPI; defaults to Google engine. |
| `http_fetch`               | `HttpFetchConnector`                     | Lightweight HTTP GET helper with retry-safe errors. |
| `semantic_scan`            | `SemanticScanConnector`                  | Summarises pages using the OpenAI Responses API when credentials are configured, otherwise uses keyword heuristics. |
| `browser_headless`         | `OpenAIBrowserConnector`                 | Delegates page capture to OpenAI’s hosted browser tool. |
| `structured_llm_extractor` | `StructuredExtractorConnector`           | Extracts happy-hour schedules via OpenAI or heuristics. |

Load the entire registry with:

```python
from agentkit.connectors import connectors

google = connectors["google_places_search"]
response = google(query="Duke's Waikiki", location_bias="point:-157.827,21.276")
print(response.data["candidates"][0]["name"])
```

## Environment Variables

| Variable                | Purpose                                           | Rate-Limit Guidance |
|------------------------|---------------------------------------------------|---------------------|
| `GOOGLE_PLACES_API_KEY`| Access token for Google Places API.               | Places search is billed per request; budget for 1 QPS during discovery. |
| `YELP_API_KEY`         | Yelp Fusion API bearer token.                     | 5000 daily calls (default). Cache responses to stay within bounds. |
| `SERP_API_KEY`         | SerpAPI key for web search.                       | Free tier: 100 searches/day. Use focused queries to reduce noise. |
| `OPENAI_API_KEY`       | Used by semantic scan, structured extraction, and browser connectors. | Responses API billing applies; use `gpt-4.1-mini` or `gpt-4o-mini` to balance cost vs. quality. |

When any variable is absent the corresponding connector automatically switches
to mock mode and adds a warning such as:

```
google_places_search used mock mode because GOOGLE_PLACES_API_KEY is not configured.
```

These warnings should be logged by the orchestrator so operators know when they
are reviewing simulated output.

## Mock Behaviour

Mocks aim to be realistic and stable:

- **Place lookup** returns a single candidate with deterministic IDs based on
  the query string.
- **Yelp search** returns a mock business seeded by query + location.
- **Web search** produces up to five placeholder results linking to
  deterministic URLs.
- **Semantic scan and structured extraction** still perform keyword heuristics
  so downstream agents receive meaningful signals even without LLM access.
- **Browser connector** reports that OpenAI credentials are missing and
  suggests enabling them for live capture.

## Smoke Test Script

Run `python scripts/smoke_connectors.py` to exercise the normalizer/discovery
happy path. The script:

1. Loads all connectors.
2. Executes the Google + Yelp lookups and the web-search connector.
3. Runs a semantic scan over the fetched snippets.
4. Prints whether each connector ran in **live** or **mock** mode.

When credentials are configured the output will include live metadata (e.g.,
Google candidate IDs). Without credentials you will still see mock data that
demonstrates the flow end-to-end.

## Local Development Tips

- Seed `.env` with the required keys and run `direnv reload` (or your preferred
  env manager) before starting the runner.
- Set `LOG_LEVEL=debug` when executing the orchestrator to capture connector
  warnings.
- Rate limit protections are not built into the connectors; rely on the caller
  (workflow runner) to throttle high-volume loops such as URL evaluation.

## Manual Verification

1. Run `python scripts/smoke_connectors.py --venue "Duke's Waikiki" --city Honolulu`.
2. Confirm the discovery queue receives at least one URL (printed in the script
   output).
3. Review the summary produced by `semantic_scan`; check that the structured
   extractor surfaces hours/specials from the sample blob.
4. For live credentials, inspect the `raw` payloads saved by the script to
   confirm API responses are flowing through without errors.
