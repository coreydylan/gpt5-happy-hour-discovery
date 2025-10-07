import { NextResponse } from "next/server";
import { getSupabaseAdmin } from "@/lib/supabaseAdmin";
import { loadContractTemplate } from "@/lib/contractTemplate";

function validateBody(body: unknown) {
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    throw new Error("Request body must be a JSON object.");
  }
  const { name, location, restaurant_slug } = body as Record<string, unknown>;
  if (!name || typeof name !== "string") {
    throw new Error("'name' is required and must be a string.");
  }
  if (!location || typeof location !== "string") {
    throw new Error("'location' is required and must be a string.");
  }
  if (!restaurant_slug || typeof restaurant_slug !== "string") {
    throw new Error("'restaurant_slug' is required and must be a string.");
  }
  return { name: name.trim(), location: location.trim(), slug: restaurant_slug.trim() };
}

export async function POST(request: Request) {
  try {
    const payload = await request.json();
    const { name, location, slug } = validateBody(payload);
    const template = await loadContractTemplate();

    const templateMetadata = isRecord(template.metadata) ? template.metadata : {};
    const templateInput = isRecord(templateMetadata.input) ? templateMetadata.input : {};

    const now = new Date().toISOString();
    const contract = {
      ...template,
      metadata: {
        ...templateMetadata,
        restaurant_slug: slug,
        input: {
          ...templateInput,
          name,
          location,
        },
        created_at:
          typeof templateMetadata.created_at === "string" ? templateMetadata.created_at : now,
        updated_at: now,
      },
    };

    const supabase = getSupabaseAdmin();
    if (supabase) {
      const { error } = await supabase
        .from("restaurant_contracts")
        .upsert(
          {
            restaurant_slug: slug,
            contract,
            created_at: now,
            updated_at: now,
          },
          { onConflict: "restaurant_slug" }
        );

      if (error) {
        throw new Error(`Supabase upsert failed: ${error.message}`);
      }
    }

    return NextResponse.json(
      {
        restaurant_slug: slug,
        contract,
        pulled_at: now,
      },
      { status: 201 }
    );
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Failed to seed restaurant contract.";
    return NextResponse.json({ message }, { status: 400 });
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
