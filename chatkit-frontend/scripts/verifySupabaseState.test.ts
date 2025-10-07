import assert from "node:assert/strict";
import test from "node:test";

import { buildVerificationContract } from "./verifySupabaseState";

test("buildVerificationContract merges metadata without mutating template", () => {
  const template = {
    version: "1.0.0",
    metadata: {
      created_at: "2024-01-01T00:00:00Z",
      input: {
        existing: "value",
      },
    },
  };

  const now = "2025-01-01T10:00:00Z";
  const slug = "test-slug";
  const name = "Verification Bistro";
  const location = "Test City";

  const contract = buildVerificationContract(template, slug, name, location, now);

  assert.equal(contract.metadata?.restaurant_slug, slug);
  assert.equal(contract.metadata?.created_at, "2024-01-01T00:00:00Z");
  assert.equal(contract.metadata?.updated_at, now);
  assert.deepEqual(contract.metadata?.input, {
    existing: "value",
    name,
    location,
  });

  assert.equal(template.metadata?.restaurant_slug, undefined);
  assert.equal(template.metadata?.updated_at, undefined);
  assert.deepEqual(template.metadata?.input, { existing: "value" });
});
