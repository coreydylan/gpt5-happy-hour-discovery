import path from "node:path";
import { readFile } from "node:fs/promises";

let cachedTemplate: Record<string, unknown> | null = null;

export async function loadContractTemplate(): Promise<Record<string, unknown>> {
  if (!cachedTemplate) {
    const templatePath = path.join(
      process.cwd(),
      "..",
      "agentkit",
      "contracts",
      "happy_hour_contract_template.json"
    );
    const raw = await readFile(templatePath, "utf-8");
    cachedTemplate = JSON.parse(raw) as Record<string, unknown>;
  }

  // Always provide a defensive copy so callers can mutate safely.
  return globalThis.structuredClone
    ? globalThis.structuredClone(cachedTemplate)
    : JSON.parse(JSON.stringify(cachedTemplate));
}
