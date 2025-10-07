#!/usr/bin/env python3
"""
Smoke test for the AgentKit connector registry.

This script intentionally avoids external dependencies beyond the standard
library so it can run in CI and local dev environments alike. When API
credentials are present the connectors will execute live calls; otherwise they
fall back to deterministic mock payloads and note the mode in their metadata.
"""

from __future__ import annotations

import argparse
import json
from typing import Dict

from agentkit.connectors import connectors


def headline(text: str) -> None:
    print("\n" + "=" * len(text))
    print(text)
    print("=" * len(text))


def run_normalizer_stage(venue: str, city: str) -> Dict[str, str]:
    headline("Normalizer Stage")

    google = connectors["google_places_search"]
    g_response = google(query=f"{venue} {city}", location_bias=f"point:-157.827,21.276")
    first_candidate = g_response.data["candidates"][0]
    print(f"Google mode: {g_response.metadata['mode']} | Candidate: {first_candidate['name']}")

    yelp = connectors["yelp_business_lookup"]
    y_response = yelp(query=venue, location=city)
    first_business = y_response.data["businesses"][0]
    print(f"Yelp mode: {y_response.metadata['mode']} | Business: {first_business['name']}")

    return {
        "google_mode": g_response.metadata["mode"],
        "yelp_mode": y_response.metadata["mode"],
        "canonical_name": first_candidate["name"],
        "yelp_slug": first_business["id"],
    }


def run_discovery_stage(venue: str, city: str) -> Dict[str, str]:
    headline("Discovery Stage")

    search = connectors["search_web"]
    s_response = search(query=f"{venue} {city} happy hour", num=3)
    print(f"Search mode: {s_response.metadata['mode']}")
    for result in s_response.data["results"]:
        print(f"  - {result['title']} -> {result['link']}")

    return {"search_mode": s_response.metadata["mode"]}


def run_semantic_analysis(sample_text: str) -> None:
    headline("Semantic Scan + Structured Extraction")

    semantic = connectors["semantic_scan"]
    s_response = semantic(content=sample_text)
    print(f"Semantic mode: {s_response.metadata['mode']} | confidence={s_response.data['confidence']}")

    extractor = connectors["structured_llm_extractor"]
    e_response = extractor(content=sample_text)
    print(f"Extractor mode: {e_response.metadata['mode']} | hours={len(e_response.data['hours'])} specials={len(e_response.data['specials'])}")

    browser = connectors["browser_headless"]
    b_response = browser(url="https://example.com")
    print(f"Browser mode: {b_response.metadata['mode']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test for HHMap connectors.")
    parser.add_argument("--venue", default="Duke's Waikiki", help="Venue name to query.")
    parser.add_argument("--city", default="Honolulu", help="City used for location bias.")
    parser.add_argument(
        "--dump-json",
        metavar="PATH",
        help="Write raw connector payloads to this file for inspection.",
    )
    args = parser.parse_args()

    normalizer_state = run_normalizer_stage(args.venue, args.city)
    discovery_state = run_discovery_stage(args.venue, args.city)

    sample_text = (
        f"{args.venue} offers happy hour Monday - Friday from 3pm - 6pm with $5 drafts "
        "and half-price wings. Weekend brunch cocktails remain full price."
    )
    run_semantic_analysis(sample_text)

    if args.dump_json:
        data = {
            "normalizer": normalizer_state,
            "discovery": discovery_state,
        }
        with open(args.dump_json, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        print(f"\nWrote summary JSON to {args.dump_json}")


if __name__ == "__main__":
    main()
