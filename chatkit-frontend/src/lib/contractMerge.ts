type JsonObject = Record<string, unknown>;

type ValueWithProvenance = {
  value?: unknown;
  sources?: unknown;
  last_checked?: string | null;
  confidence?: number | null;
};

type OverrideEntry = {
  previous: unknown;
  incoming: unknown;
  needs_review: true;
  reason: string;
};

export type MergeDiagnostics = {
  accepted: string[];
  rejected: { path: string; reason: string }[];
  conflicts: string[];
  notes: string[];
};

export type MergeResult = {
  contract: JsonObject;
  overrides: Record<string, OverrideEntry>;
  diagnostics: MergeDiagnostics;
};

const EPSILON = 1e-6;

export function mergeContract(
  existingContract: JsonObject,
  patch: JsonObject,
  { now = new Date().toISOString() }: { now?: string } = {}
): MergeResult {
  const base = deepClone(existingContract);
  const diagnostics: MergeDiagnostics = {
    accepted: [],
    rejected: [],
    conflicts: [],
    notes: [],
  };

  const { overrides } = mergeNode("", base, patch, diagnostics);

  ensureMetadata(base, now);
  applyOverrides(base, overrides);
  diagnostics.notes.push(
    `Merge completed at ${now}. Updated overrides count: ${Object.keys(overrides).length}`
  );

  return {
    contract: base,
    overrides,
    diagnostics,
  };
}

function mergeNode(
  path: string,
  target: unknown,
  incoming: unknown,
  diagnostics: MergeDiagnostics
): { value: unknown; overrides: Record<string, OverrideEntry> } {
  if (incoming === undefined) {
    return { value: target, overrides: {} };
  }

  if (isValueWithProvenance(target) && isValueWithProvenance(incoming)) {
    const result = mergeValueWithProvenance(path, target, incoming, diagnostics);
    return { value: result.value, overrides: result.overrides };
  }

  if (Array.isArray(target) && Array.isArray(incoming)) {
    const merged = mergeArrays(path, target, incoming, diagnostics);
    return { value: merged, overrides: {} };
  }

  if (isJsonObject(target) && isJsonObject(incoming)) {
    const overrides: Record<string, OverrideEntry> = {};
    const targetObject = target as JsonObject;
    for (const key of Object.keys(incoming)) {
      const nextPath = path ? `${path}.${key}` : key;
      const incomingValue = incoming[key];
      if (incomingValue === undefined) {
        continue;
      }

      if (key === "sources" && Array.isArray(targetObject[key]) && Array.isArray(incomingValue)) {
        const mergedSources = uniqueStrings([...targetObject[key], ...incomingValue]);
        if (mergedSources.length !== (targetObject[key] as unknown[]).length) {
          diagnostics.accepted.push(`${nextPath}`);
        }
        targetObject[key] = mergedSources;
        continue;
      }

      if (targetObject[key] === undefined) {
        targetObject[key] = deepClone(incomingValue);
        diagnostics.accepted.push(nextPath);
        continue;
      }

      const result = mergeNode(nextPath, targetObject[key], incomingValue, diagnostics);
      targetObject[key] = result.value as never;
      Object.assign(overrides, result.overrides);
    }
    return { value: targetObject, overrides };
  }

  if (!deepEqual(target, incoming)) {
    diagnostics.accepted.push(path || "root");
    return { value: deepClone(incoming), overrides: {} };
  }

  return { value: target, overrides: {} };
}

function mergeValueWithProvenance(
  path: string,
  existing: ValueWithProvenance,
  incoming: ValueWithProvenance,
  diagnostics: MergeDiagnostics
): { value: ValueWithProvenance; overrides: Record<string, OverrideEntry> } {
  const overrides: Record<string, OverrideEntry> = {};
  const merged: ValueWithProvenance = {
    ...existing,
    sources: mergeSources(existing.sources, incoming.sources),
  };

  const existingHasValue = existing.value !== undefined && existing.value !== null;
  const incomingHasValue = incoming.value !== undefined && incoming.value !== null;

  if (!existingHasValue && incomingHasValue) {
    diagnostics.accepted.push(path);
    merged.value = cloneIfNeeded(incoming.value);
    merged.confidence = pickConfidence(incoming.confidence);
    merged.last_checked = pickTimestamp(incoming.last_checked);
    return { value: merged, overrides };
  }

  if (!incomingHasValue) {
    diagnostics.rejected.push({ path, reason: "incoming_missing_value" });
    return { value: merged, overrides };
  }

  const comparison = compareConfidence(existing.confidence, incoming.confidence);
  const timestampComparison = compareTimestamps(existing.last_checked, incoming.last_checked);
  const valuesEqual = deepEqual(existing.value, incoming.value);

  if (comparison < 0) {
    diagnostics.accepted.push(path);
    merged.value = cloneIfNeeded(incoming.value);
    merged.confidence = pickConfidence(incoming.confidence);
    merged.last_checked = selectTimestamp(existing.last_checked, incoming.last_checked);
    return { value: merged, overrides };
  }

  if (comparison === 0 && timestampComparison < 0) {
    diagnostics.accepted.push(path);
    merged.value = cloneIfNeeded(incoming.value);
    merged.confidence = pickConfidence(incoming.confidence);
    merged.last_checked = pickTimestamp(incoming.last_checked);
    return { value: merged, overrides };
  }

  if (!valuesEqual) {
    const reason =
      comparison > 0
        ? "higher_existing_confidence"
        : timestampComparison > 0
        ? "existing_newer_timestamp"
        : "comparable_confidence_conflict";
    diagnostics.conflicts.push(path);
    diagnostics.rejected.push({ path, reason });
    overrides[path] = {
      previous: cloneIfNeeded(existing.value),
      incoming: cloneIfNeeded(incoming.value),
      needs_review: true,
      reason,
    };
  } else {
    diagnostics.rejected.push({ path, reason: "duplicate_value" });
  }

  // Preserve strongest confidence/timestamp even when rejecting value.
  merged.confidence = selectConfidence(existing.confidence, incoming.confidence);
  merged.last_checked = selectTimestamp(existing.last_checked, incoming.last_checked);

  return { value: merged, overrides };
}

function mergeArrays(
  path: string,
  existing: unknown[],
  incoming: unknown[],
  diagnostics: MergeDiagnostics
): unknown[] {
  if (incoming.length === 0) {
    diagnostics.rejected.push({ path, reason: "incoming_empty_array" });
    return existing;
  }

  const merged: unknown[] = existing.map((item) => deepClone(item));
  const seen = new Set<string>(existing.map((item) => stableStringify(item)));

  for (const item of incoming) {
    const key = stableStringify(item);
    if (!seen.has(key)) {
      seen.add(key);
      merged.push(deepClone(item));
      diagnostics.accepted.push(`${path}[append]`);
    } else {
      diagnostics.rejected.push({ path, reason: "duplicate_array_entry" });
    }
  }

  return merged;
}

function ensureMetadata(contract: JsonObject, now: string) {
  if (!isJsonObject(contract.metadata)) {
    contract.metadata = {};
  }

  const metadata = contract.metadata as JsonObject;

  if (!isJsonObject(metadata.input)) {
    metadata.input = {};
  }

  metadata.updated_at = now;
}

function applyOverrides(
  contract: JsonObject,
  overrides: Record<string, OverrideEntry>
) {
  const bucket = isJsonObject(contract.overrides) ? { ...contract.overrides } : {};
  for (const [path, entry] of Object.entries(overrides)) {
    bucket[path] = entry;
  }
  contract.overrides = bucket;
}

function mergeSources(
  existing: unknown,
  incoming: unknown
): string[] | undefined {
  const existingArr = Array.isArray(existing) ? existing : [];
  const incomingArr = Array.isArray(incoming) ? incoming : [];
  const merged = uniqueStrings([...existingArr, ...incomingArr]);
  return merged.length > 0 ? merged : undefined;
}

function uniqueStrings(values: unknown[]): string[] {
  const set = new Set<string>();
  for (const value of values) {
    if (typeof value === "string" && value.trim().length > 0) {
      set.add(value.trim());
    }
  }
  return Array.from(set);
}

function compareConfidence(
  existing: number | null | undefined,
  incoming: number | null | undefined
): number {
  const existingNormalized = normalizeNumber(existing);
  const incomingNormalized = normalizeNumber(incoming);
  if (incomingNormalized === null && existingNormalized === null) {
    return 0;
  }
  if (incomingNormalized === null) {
    return 1;
  }
  if (existingNormalized === null) {
    return -1;
  }
  if (incomingNormalized > existingNormalized + EPSILON) {
    return -1;
  }
  if (existingNormalized > incomingNormalized + EPSILON) {
    return 1;
  }
  return 0;
}

function compareTimestamps(
  existingTimestamp: string | null | undefined,
  incomingTimestamp: string | null | undefined
): number {
  const existingValue = Date.parse(existingTimestamp ?? "");
  const incomingValue = Date.parse(incomingTimestamp ?? "");

  if (Number.isNaN(existingValue) && Number.isNaN(incomingValue)) {
    return 0;
  }
  if (Number.isNaN(incomingValue)) {
    return 1;
  }
  if (Number.isNaN(existingValue)) {
    return -1;
  }

  if (incomingValue > existingValue) {
    return -1;
  }
  if (existingValue > incomingValue) {
    return 1;
  }
  return 0;
}

function selectTimestamp(
  existingTimestamp: string | null | undefined,
  incomingTimestamp: string | null | undefined
): string | null | undefined {
  const comparison = compareTimestamps(existingTimestamp, incomingTimestamp);
  if (comparison <= 0) {
    return incomingTimestamp ?? existingTimestamp ?? null;
  }
  return existingTimestamp ?? incomingTimestamp ?? null;
}

function pickTimestamp(timestamp: string | null | undefined): string | null | undefined {
  return timestamp ?? null;
}

function selectConfidence(
  existing: number | null | undefined,
  incoming: number | null | undefined
): number | null | undefined {
  const comparison = compareConfidence(existing, incoming);
  if (comparison <= 0) {
    return pickConfidence(incoming);
  }
  return pickConfidence(existing);
}

function pickConfidence(value: number | null | undefined): number | null | undefined {
  const normalized = normalizeNumber(value);
  return normalized ?? null;
}

function normalizeNumber(value: number | null | undefined): number | null {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return null;
  }
  return value;
}

function deepClone<T>(value: T): T {
  if (value === undefined) {
    return value;
  }
  if (typeof globalThis.structuredClone === "function") {
    return globalThis.structuredClone(value);
  }
  return JSON.parse(JSON.stringify(value));
}

function cloneIfNeeded(value: unknown): unknown {
  return isJsonObject(value) || Array.isArray(value) ? deepClone(value) : value;
}

function stableStringify(value: unknown): string {
  return JSON.stringify(value, (_, innerValue) => {
    if (innerValue && typeof innerValue === "object" && !Array.isArray(innerValue)) {
      return Object.keys(innerValue)
        .sort()
        .reduce<Record<string, unknown>>((acc, key) => {
          acc[key] = (innerValue as JsonObject)[key];
          return acc;
        }, {});
    }
    return innerValue;
  });
}

function deepEqual(a: unknown, b: unknown): boolean {
  return stableStringify(a) === stableStringify(b);
}

function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isValueWithProvenance(value: unknown): value is ValueWithProvenance {
  if (!isJsonObject(value)) return false;
  if (!("value" in value)) return false;
  return true;
}
