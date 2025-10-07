import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { config as loadEnv } from "dotenv";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { randomUUID } from "node:crypto";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

loadEnv({ path: path.resolve(__dirname, "..", ".env.local"), override: false });
loadEnv({ path: path.resolve(__dirname, "..", ".env"), override: false });

type ContractMetadata = {
  input?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
  [key: string]: unknown;
};

type ContractTemplate = Record<string, unknown> & {
  metadata?: ContractMetadata;
};

type ContractPayload = ContractTemplate & {
  metadata: ContractMetadata & {
    restaurant_slug: string;
    created_at: string;
    updated_at: string;
    input: Record<string, unknown>;
  };
};

type VerificationSummary = {
  restaurantSlug: string;
  urlQueueTaskIds: string[];
  extractionQueueTaskId: string;
  agentLogId: string;
};

type VerificationOptions = {
  skipCleanup?: boolean;
};

async function loadTemplate(): Promise<ContractTemplate> {
  const templatePath = path.resolve(__dirname, "..", "..", "agentkit", "contracts", "happy_hour_contract_template.json");
  const raw = await readFile(templatePath, "utf-8");
  return JSON.parse(raw);
}

export function requireEnvVar(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

export function buildVerificationContract(
  template: ContractTemplate,
  slug: string,
  name: string,
  location: string,
  now = new Date().toISOString()
): ContractPayload {
  const metadata: ContractMetadata = {
    ...(template.metadata ?? {}),
  };

  const input =
    template.metadata?.input && typeof template.metadata.input === "object" && !Array.isArray(template.metadata.input)
      ? { ...(template.metadata.input as Record<string, unknown>) }
      : {};

  return {
    ...template,
    metadata: {
      ...metadata,
      restaurant_slug: slug,
      created_at: metadata.created_at ?? now,
      updated_at: now,
      input: {
        ...input,
        name,
        location,
      },
    },
  };
}

async function verifySupabaseState(
  supabase: SupabaseClient,
  { skipCleanup = false }: VerificationOptions = {}
): Promise<VerificationSummary> {
  const slug = `hhmap-verification-${Date.now()}`;
  const taskId = randomUUID();
  const extractionTaskId = randomUUID();
  const agentLogId = randomUUID();

  const [template, now] = await Promise.all([loadTemplate(), Promise.resolve(new Date().toISOString())]);
  const contract = buildVerificationContract(template, slug, "Verification Bistro", "Test City, ST", now);

  const { error: contractError } = await supabase.from("restaurant_contracts").upsert(
    {
      restaurant_slug: slug,
      contract,
      created_at: now,
      updated_at: now,
    },
    { onConflict: "restaurant_slug" }
  );

  if (contractError) {
    throw new Error(`Failed to upsert restaurant_contracts row: ${contractError.message}`);
  }

  const { error: readContractError } = await supabase
    .from("restaurant_contracts")
    .select("restaurant_slug")
    .eq("restaurant_slug", slug)
    .maybeSingle();

  if (readContractError) {
    throw new Error(`Failed to read back restaurant_contracts row: ${readContractError.message}`);
  }

  const { error: urlQueueError } = await supabase.from("happy_hour_url_queue").upsert(
    [
      {
        task_id: taskId,
        restaurant_slug: slug,
        url: "https://example.com/menu",
        why_interesting: "Verification script seed",
        status: "pending",
      },
      {
        restaurant_slug: slug,
        url: "https://example.com/happy-hour",
        why_interesting: "Verification script seed",
        status: "pending",
      },
    ],
    { onConflict: "restaurant_slug,url" }
  );

  if (urlQueueError) {
    throw new Error(`Failed to verify happy_hour_url_queue access: ${urlQueueError.message}`);
  }

  const { error: extractionQueueError } = await supabase.from("happy_hour_extraction_queue").insert({
    task_id: extractionTaskId,
    restaurant_slug: slug,
    source_url: "https://example.com/happy-hour",
    instructions: { note: "Verification script seed" },
    status: "pending",
  });

  if (extractionQueueError) {
    throw new Error(`Failed to verify happy_hour_extraction_queue access: ${extractionQueueError.message}`);
  }

  const { error: agentLogError } = await supabase.from("agent_run_logs").insert({
    id: agentLogId,
    restaurant_slug: slug,
    agent_id: "verification-script",
    task_id: extractionTaskId,
    status: "queued",
    payload: { note: "Verification script seed" },
  });

  if (agentLogError) {
    throw new Error(`Failed to verify agent_run_logs access: ${agentLogError.message}`);
  }

  if (!skipCleanup) {
    await cleanupVerificationData(supabase, {
      slug,
      extractionTaskId,
      agentLogId,
    });
  }

  return {
    restaurantSlug: slug,
    urlQueueTaskIds: [taskId],
    extractionQueueTaskId: extractionTaskId,
    agentLogId,
  };
}

async function cleanupVerificationData(
  supabase: SupabaseClient,
  {
    slug,
    extractionTaskId,
    agentLogId,
  }: {
    slug: string;
    extractionTaskId: string;
    agentLogId: string;
  }
) {
  await Promise.all([
    supabase.from("happy_hour_url_queue").delete().eq("restaurant_slug", slug),
    supabase.from("happy_hour_extraction_queue").delete().eq("task_id", extractionTaskId),
    supabase.from("agent_run_logs").delete().eq("id", agentLogId),
    supabase.from("restaurant_contracts").delete().eq("restaurant_slug", slug),
  ]);
}

export async function runVerification(options: VerificationOptions = {}): Promise<VerificationSummary> {
  const url = requireEnvVar("SUPABASE_URL");
  const key = requireEnvVar("SUPABASE_SERVICE_ROLE_KEY");

  const supabase = createClient(url, key, {
    auth: {
      persistSession: false,
    },
  });

  return verifySupabaseState(supabase, options);
}

async function main() {
  const scriptPath = fileURLToPath(import.meta.url);
  const scriptIndex = process.argv.findIndex((arg) => path.resolve(arg) === scriptPath);
  const cliArgs = scriptIndex >= 0 ? process.argv.slice(scriptIndex + 1) : [];
  const skipCleanup = cliArgs.includes("--keep") || cliArgs.includes("--no-cleanup");

  try {
    const summary = await runVerification({ skipCleanup });
    console.info("✅ Supabase state verification completed.");
    console.info(`   restaurant_contracts slug: ${summary.restaurantSlug}`);
    console.info(`   happy_hour_url_queue task ids: ${summary.urlQueueTaskIds.join(", ") || "n/a"}`);
    console.info(`   happy_hour_extraction_queue task id: ${summary.extractionQueueTaskId}`);
    console.info(`   agent_run_logs id: ${summary.agentLogId}`);
    if (skipCleanup) {
      console.info("⚠️  Cleanup skipped. Remove verification rows manually when finished testing.");
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    console.error(`❌ Verification failed: ${message}`);
    process.exitCode = 1;
  }
}

const scriptPath = fileURLToPath(import.meta.url);
const invokedDirectly = process.argv.some((arg, index) => index > 0 && path.resolve(arg) === scriptPath);

if (invokedDirectly) {
  void main();
}

export { verifySupabaseState };
