import assert from "node:assert/strict";
import test from "node:test";

import { mergeContract } from "./contractMerge";

const BASE_CONTRACT = {
  version: "1.0.0",
  metadata: {
    restaurant_slug: "test-slug",
    input: { name: "Example", location: "City" },
    created_at: "2024-01-01T00:00:00.000Z",
    updated_at: "2024-01-02T00:00:00.000Z",
  },
  restaurant: {
    name: {
      value: "Example",
      sources: ["source:a"],
      last_checked: "2024-01-01T00:00:00.000Z",
      confidence: 0.6,
    },
  },
  happy_hour: {
    status: "unknown",
    timeframes: [
      {
        days: ["monday"],
        start: "16:00",
        end: "18:00",
        sources: ["source:a"],
        last_checked: "2024-01-01T00:00:00.000Z",
      },
    ],
    categories: {
      drinks: {
        discounts: [],
        items: [],
      },
      food: {
        discounts: [],
        items: [],
      },
    },
  },
  overrides: {},
};

test("mergeContract accepts updates with higher confidence", () => {
  const patch = {
    restaurant: {
      name: {
        value: "Example Bistro",
        sources: ["source:b"],
        last_checked: "2025-01-01T00:00:00.000Z",
        confidence: 0.9,
      },
    },
  };

  const { contract, diagnostics } = mergeContract(
    BASE_CONTRACT,
    patch,
    { now: "2025-02-01T00:00:00.000Z" }
  );

  const name = (contract.restaurant as Record<string, unknown>).name as Record<string, unknown>;
  assert.equal(name.value, "Example Bistro");
  assert.deepEqual(name.sources, ["source:a", "source:b"]);
  assert.equal(name.confidence, 0.9);
  assert.equal(name.last_checked, "2025-01-01T00:00:00.000Z");
  const metadata = contract.metadata as Record<string, unknown>;
  assert.equal(metadata.updated_at, "2025-02-01T00:00:00.000Z");
  assert.equal(diagnostics.conflicts.length, 0);
});

test("mergeContract retains existing value when incoming confidence is lower and logs override", () => {
  const patch = {
    restaurant: {
      name: {
        value: "Conflicting Name",
        sources: ["source:b"],
        last_checked: "2023-12-01T00:00:00.000Z",
        confidence: 0.4,
      },
    },
  };

  const { contract, diagnostics } = mergeContract(
    BASE_CONTRACT,
    patch,
    { now: "2025-02-01T00:00:00.000Z" }
  );

  const mergedName = (contract.restaurant as Record<string, unknown>).name as Record<string, unknown>;
  assert.equal(mergedName.value, "Example");

  const overrides = contract.overrides as Record<string, unknown>;
  const entry = overrides["restaurant.name"] as Record<string, unknown>;
  assert.ok(entry);
  assert.equal(entry.needs_review, true);
  assert.equal(entry.reason, "higher_existing_confidence");
  assert.equal(entry.previous, "Example");
  assert.equal(entry.incoming, "Conflicting Name");
  assert.equal(diagnostics.conflicts.length, 1);

  assert.deepEqual(mergedName.sources, ["source:a", "source:b"]);
});

test("mergeContract appends unique timeframe entries without duplication", () => {
  const patch = {
    happy_hour: {
      timeframes: [
        {
          days: ["tuesday"],
          start: "17:00",
          end: "19:00",
          sources: ["source:c"],
          last_checked: "2025-01-05T00:00:00.000Z",
        },
        {
          days: ["monday"],
          start: "16:00",
          end: "18:00",
          sources: ["source:a"],
          last_checked: "2024-01-01T00:00:00.000Z",
        },
      ],
    },
  };

  const { contract } = mergeContract(
    BASE_CONTRACT,
    patch,
    { now: "2025-02-01T00:00:00.000Z" }
  );

  const timeframes = (contract.happy_hour as Record<string, unknown>).timeframes as unknown[];
  assert.equal(timeframes.length, 2);
});
