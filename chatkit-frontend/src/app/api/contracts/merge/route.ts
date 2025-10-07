import { NextResponse } from "next/server";
import { getSupabaseAdmin } from "@/lib/supabaseAdmin";
import { loadContractTemplate } from "@/lib/contractTemplate";
import { mergeContract } from "@/lib/contractMerge";

type MergeRequestBody = {
  restaurant_slug?: unknown;
  patch?: unknown;
};

const REQUIRED_FIELDS = ["restaurant_slug", "patch"] as const;

export async function POST(request: Request) {
  try {
    const payload = (await request.json()) as MergeRequestBody;
    validateBody(payload);

    const slug = String(payload.restaurant_slug).trim();
    const patch = payload.patch as Record<string, unknown>;
    const now = new Date().toISOString();

    const existing = await loadExistingContract(slug);
    const { contract, diagnostics } = mergeContract(existing, patch, { now });

    ensureMetadata(contract, slug, now);

    await persistContract(slug, contract, now);

    const summaryPayload = {
      slug,
      accepted: diagnostics.accepted.length,
      rejected: diagnostics.rejected.length,
      conflicts: diagnostics.conflicts.length,
    };
    console.info("[contracts.merge] merge completed", JSON.stringify(summaryPayload));

    if (diagnostics.conflicts.length > 0) {
      console.warn(
        "[contracts.merge] conflicts detected",
        JSON.stringify({ slug, conflicts: diagnostics.conflicts })
      );
    }

    return NextResponse.json(
      {
        restaurant_slug: slug,
        contract,
        diagnostics,
      },
      { status: 200 }
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Merge operation failed.";
    console.error("[contracts.merge] error", message);
    return NextResponse.json({ message }, { status: 400 });
  }
}

function validateBody(payload: MergeRequestBody) {
  for (const field of REQUIRED_FIELDS) {
    if (!(field in payload)) {
      throw new Error(`Missing required field '${field}'.`);
    }
  }

  if (typeof payload.restaurant_slug !== "string" || payload.restaurant_slug.trim().length === 0) {
    throw new Error("'restaurant_slug' must be a non-empty string.");
  }

  if (!payload.patch || typeof payload.patch !== "object" || Array.isArray(payload.patch)) {
    throw new Error("'patch' must be a JSON object.");
  }
}

async function loadExistingContract(slug: string): Promise<Record<string, unknown>> {
  const supabase = getSupabaseAdmin();
  if (!supabase) {
    return loadContractTemplate();
  }

  const { data, error } = await supabase
    .from("restaurant_contracts")
    .select("contract")
    .eq("restaurant_slug", slug)
    .maybeSingle();

  if (error) {
    throw new Error(`Supabase query failed: ${error.message}`);
  }

  if (!data?.contract) {
    return loadContractTemplate();
  }

  if (!isJsonObject(data.contract)) {
    throw new Error("Stored contract is invalid.");
  }

  return data.contract;
}

async function persistContract(
  slug: string,
  contract: Record<string, unknown>,
  now: string
) {
  const supabase = getSupabaseAdmin();
  if (!supabase) {
    return;
  }

  const { error } = await supabase
    .from("restaurant_contracts")
    .upsert(
      {
        restaurant_slug: slug,
        contract,
        created_at: extractCreatedAt(contract.metadata) ?? now,
        updated_at: now,
      },
      { onConflict: "restaurant_slug" }
    );

  if (error) {
    throw new Error(`Supabase upsert failed: ${error.message}`);
  }
}

function ensureMetadata(contract: Record<string, unknown>, slug: string, now: string) {
  if (!isJsonObject(contract.metadata)) {
    contract.metadata = {};
  }

  const metadata = contract.metadata as Record<string, unknown>;
  metadata.restaurant_slug = slug;

  if (!isJsonObject(metadata.input)) {
    metadata.input = {};
  }

  if (metadata.created_at === undefined || metadata.created_at === null) {
    metadata.created_at = now;
  }

  metadata.updated_at = now;
}

function isJsonObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function extractCreatedAt(
  metadata: unknown
): string | null | undefined {
  if (!isJsonObject(metadata)) {
    return undefined;
  }
  const createdAt = metadata.created_at;
  return typeof createdAt === "string" ? createdAt : undefined;
}
