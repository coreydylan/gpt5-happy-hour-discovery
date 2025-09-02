Skip to content
Chat history

You said:
im building a GPT5 based tool that takes the input of a restaurant with as much data abotu that restaurnat as we have and then deploys agents to search sources to find out all the details about that locations happy hour offerings, it has a lengthy and defined json contract it must full out using gpt5 structed outputs required guaranteed json structures and it has to report all the details it finds about the happy hour or report it couldntfind a detail if it cant and can flag some for human review - what im wondering is how we can make this extremely powerful by giving it access to as many different sources as it could possibly need to find the data - im talking isntagram comment threads and reviews on google and yelp and i want you to come up with a bunch of different other sources we could go out and find - because what i want to happen is for each of the agents to send back their best abiltiy to fill out the detailed json with what it finds, and then all those json's get submitted to something determinsitic that develops confidence scores in each element of the data on the json based on what all the agents sent back, and the agents have to report dates with their data so that recency can be included in the confidence score....... take this idea and extend it out to it's nTH degree
ChatGPT said:

Thought for 1m 8s
Corey, this is a great problem to overbuild, because happy hours are messy, localized, and constantly changing. If you nail freshness, provenance, and conflict resolution, you’ll own this niche. Here’s the full play: a source-universe that’s way bigger than “Google + Yelp,” an agent mesh that extracts with receipts, and a deterministic judge that fuses everything into one JSON with calibrated confidence and flags for humans only when it truly matters.
I’m going to give you:

the complete source map, 2) the multi-agent architecture, 3) the deterministic consensus model with math, 4) a battle-tested JSON contract shape, 5) adversarial checks, 6) how to keep it fresh, and 7) a blunt build plan.
1) Source universe (think in tiers by trust and recency)
Tier A — “Owner-authored” or near-official
Restaurant website pages: “Happy Hour,” “Menus,” often PDF or Popmenu/BentoBox pages. Popmenu and BentoBox are everywhere and frequently updated. 
get.popmenu.com
+1
Google Business Profile: Posts, Q&A, Hours attributes, “Menu link.” Q&A threads often contain exact times, sometimes corrected by owners or super-users. 
BrightLocal
Google Help
Reservations/CRM stacks with event modules that leak HH info: Resy/OpenTable/SevenRooms/Tock. Resy in particular promotes events and has owner-managed data that sometimes includes HH lines. Use it as a strong signal when present. 
Resy
+2
Resy
+2
Email/newsletters and site RSS feeds (many restaurant CMSs quietly expose feeds).
The “just call” lane: a voice bot that asks a 20-second, yes/no structured script and records consented confirmations.
Tier B — “High-coverage, user-generated”
Google reviews and Q&A for “happy hour,” “HH,” “margarita Monday,” “half-off apps,” etc.
Yelp reviews and photos; Yelp’s Fusion API gives you programmatic access to business data and some reviews, though full review access is gated by plan/partnership. Treat as partial but valuable.
docs.developer.yelp.com
+2
docs.developer.yelp.com
+2
Stack Overflow
Facebook Page posts/events.
Instagram posts, Stories, Story Highlights, Reels, and especially comment threads where staff reply to hours or exclusions.
TikTok captions around geotagged venues; comments often correct times.
Tier C — “Specials and beverage ecosystems”
Untappd for Business and BeerMenus. Bars often keep these current; menus frequently include time-bound specials. Great for drink-focused HH. 
Untappd for Business™
+1
BeerMenus
Local beer lists on brewery collab pages, Tap lists in POS-connected displays.
Tier D — “Editorial and deal aggregators”
Eater, Thrillist, Time Out, alt-weeklies, local food blogs. They age quickly but still useful for last-known baseline.
Groupon/LivingSocial and local “$1 oysters” roundups.
Reddit city subs (“happy hour” megathreads), Discord foodie servers.
Tier E — “Signals and edge cases”
Online ordering menus (Toast/Square/ChowNow) sometimes label “HH” categories when toggled on, time-gated.
DoorDash/Uber Eats/Grubhub often don’t show HH, but name collisions or time-based promos can hint.
Wayback Machine on the restaurant site for “was HH removed last month?”
City event calendars and BIDs (First Friday = no HH).
Sports calendars to detect “game-day pricing” exceptions.
Opinionated weighting: Tier A > B > C > D > E. Instagram comments can be gold, but volatile. Yelp has breadth, but use it to corroborate owner data, not to overrule it unless it’s extremely specific and recent.
2) Multi-agent system (orchestrated like a newsroom)
Orchestrator
Receives a restaurant entity {name, address, phone, website, lat/lng, social handles, known platforms} and fans out work.
Agents (specialists, not generalists):

SiteAgent: Crawls website, follows “/menu”, “/happy-hour”, PDFs; runs OCR if images.
GoogleAgent: Scrapes Business Profile details, Posts, Q&A; harvests menu link.
YelpAgent: Uses Fusion API for business and available reviews; scrapes photos metadata if allowed by ToS.
SocialAgents: InstagramAgent, FacebookAgent, TikTokAgent that:
pull posts/captions/comments, scan Highlights named “Happy Hour,” run OCR on flyers, extract times and exclusions.
Resy/OpenTable/SevenRooms/TockAgent: If the venue is present, pull event/notes fields and “experiences” that mention HH. 
Resy
BeverageAgent: Untappd/BeerMenus ingestion. 
Untappd for Business™
+1
OrderingAgent: Scans Toast/Square pages for HH-labeled categories.
EditorialAgent: Pulls Eater/Thrillist/blog posts; marks all data as “historical” with decay.
VoiceVerifyAgent (killer feature): Calls the venue with a short decision tree. Example:
“Do you currently offer happy hour?”
“Which days and what times?”
“Bar only or full restaurant?”
“Any exclusions, game days, holidays?”
Captures a recording, transcript, employee first name, and timestamp. High trust with moderate decay.
Extractors shared by all agents:
Text normalizer, timezone resolver, phone/site/handle resolver.
NER for items, price, day-of-week, times, exclusions (“bar area only,” “not on holidays,” “not valid with other offers”).
Visual OCR pipeline for menus and story screenshots.
Temporal parser that understands “Mon–Fri 3–6”, “daily 9–close,” “industry night Mondays.”
Normalizers for currency, DST, and business hours overlap.
Each agent returns only strict JSON to your contract and includes an evidence pack per field:
{
  "field": "schedule.weekly",
  "value": {"mon":[{"start":"15:00","end":"18:00"}], ...},
  "source": "instagram_comment",
  "source_url": "https://instagram.com/p/…",
  "observed_at": "2025-09-01T23:04:00Z",
  "snippet": "Happy hour M–F 3–6! Bar only.",
  "specificity": "exact_time_window",
  "modality": "text|image_ocr|voice",
  "agent_confidence": 0.82
}
3) Deterministic consensus (truth-finding with recency)
Treat every field as a small truth-discovery problem. No “vibes.” A simple, fast model:
Per-source trust weight: w_source by tier and known reliability.
Recency decay: w_time = exp(-age_days / half_life). Use HL=30d for normal, 7d for sports-bar markets, 3d for Vegas-style venues.
Specificity bonus: +b for exact times, itemized prices, and staff-authored comments.
Contradiction penalty: If two candidates overlap but conflict, subtract penalty proportional to their closeness.

For each candidate value v for a field F:

support(v) = Σ_i [ w_source(i) * w_time(i) * s_specificity(i) * s_agent(i) ]
score(v) = σ( support(v) - contradiction_penalty(v) )
Pick the argmax. If top-1 minus top-2 < δ, flag F for human review.
Calibrate the weights on a labeled set you create by running the VoiceVerifyAgent on 200 venues across segments.

Element-level scoring: Do this per tiny atom, not just the whole object. Example: Monday window vs Tuesday window vs “bar-only” vs “$1 off drafts.”

4) JSON contract (lean but expressive)
Design it so you can show your work, not just the answer.
{
  "venue": {
    "name": "The Example",
    "address": "123 A St, San Diego, CA 92101",
    "phone": "+1-619-555-1212",
    "website": "https://example.com",
    "timezone": "America/Los_Angeles",
    "platform_ids": {
      "google_place_id": "…",
      "yelp_business_id": "…",
      "resy_slug": "…",
      "instagram": "@examplebar"
    }
  },
  "happy_hour": {
    "status": "active|unknown|discontinued",
    "schedule": {
      "weekly": {
        "mon":[{"start":"15:00","end":"18:00"}],
        "tue":[{"start":"15:00","end":"18:00"}],
        "wed":[{"start":"15:00","end":"18:00"}],
        "thu":[{"start":"15:00","end":"18:00"}],
        "fri":[{"start":"15:00","end":"18:00"}],
        "sat":[],
        "sun":[]
      },
      "blackouts": [
        {"rule":"closed_holidays"},
        {"rule":"no_hh_on_home_games","notes":"Padres game days"}
      ],
      "areas": ["bar_only","patio_ok|unknown"],
      "dine_in_only": true
    },
    "offers": [
      {"category":"beer","item":"draft beer","price":5.00,"unit":"USD","notes":"domestics"},
      {"category":"food","item":"oysters","price":1.50,"unit":"USD","notes":"while supplies last"}
    ],
    "fine_print": [
      "Not valid with other discounts",
      "Must sit at the bar"
    ]
  },
  "provenance": {
    "compiled_at": "2025-09-01T23:04:00Z",
    "fields": {
      "schedule.weekly.mon[0]": {
        "value": {"start":"15:00","end":"18:00"},
        "confidence": 0.93,
        "evidence": [
          {"source":"website","url":"…","observed_at":"…"},
          {"source":"google_post","url":"…","observed_at":"…"},
          {"source":"instagram_comment","url":"…","observed_at":"…"}
        ],
        "conflicts":[
          {"value":{"start":"16:00","end":"18:00"},"source":"yelp_review","observed_at":"…"}
        ]
      }
    }
  },
  "qa": {
    "could_not_find": ["blackouts[1] exact list"],
    "needs_review": ["areas"],
    "notes_for_human": "IG says ‘bar only’; website ambiguous."
  }
}
Non-negotiables for reliability
Strict output guarantees from GPT-5 structured mode. Reject-on-fail and retry with function calling.
Every field has zero or more evidence items. If no evidence, you must either mark could_not_find or set status: unknown. No hallucinated defaults.
5) Adversarial checks before you trust a result
Temporal coherence: Don’t accept “Mon–Fri 3–6” if the venue is closed at 3 on Tuesdays.
Map overlap: If “bar only,” ensure the venue has a bar area at all. If not known, lower confidence or flag.
Textual contradictions: “All day Monday” vs “3–6” on a Monday flyer last week. Prefer newer and owner-authored if within 45 days.
Unit sanity: $0 oysters? $50 well drinks? Flag.
Game-day exceptions: Use local team schedules for venues that advertise game-day pricing.
Image-OCR cross-check: Extracted times must appear on the same image as “Happy Hour” within 200px or same bounding box cluster.
Name collision: Ensure you have the right “Corner Bar” in the right city via phone, website domain, and lat/lng.
6) Freshness and change detection
Decay math: Default half-life 30 days, accelerate to 14 for beach towns in summer and 7 for sports bars in season.
Watchers:
Website: hash the HH section or PDF and diff.
Instagram: subscribe to new posts; re-run OCR when a post contains “happy” or a clock emoji.
Google Q&A: poll for new answers containing “hour,” “happy,” “3–6,” “$”. 
BrightLocal
Untappd/BeerMenus: poll menu revisions. 
Untappd for Business™
+1
Trigger a mini-crawl when: new evidence arrives, a user reports wrong info, or your VoiceVerifyAgent fails twice.
7) Adapters and legality
Use official APIs where possible (Yelp Fusion, etc.). Respect rate limits and ToS. Some sources restrict scraping or comments access. Plan for “partnership lanes” to elevate access over time.
docs.developer.yelp.com
+1
For Instagram and others, you’ll need authenticated headless browsing with conservative rates, rotating residential IPs, and strong backoff, or work with social listening vendors. Build a “compliance mode” switch per tenant.
8) Confidence scoring recipe (concrete)
Set source weights like:
Website/owner email/voice-confirm: 1.0
Google Post/Q&A owner-answered: 0.85
Reservation platform notes: 0.75
Untappd/BeerMenus live menu: 0.7
Google/Yelp reviews: 0.5 (but +0.1 if the text contains exact day/time and price)
Editorial/blog: 0.3
Recency: w_time = exp(-age_days / HL) with HL chosen per venue type.
Specificity:

Exact time window: 1.2
Price with currency: 1.15
Vague (“afternoon”): 0.8
Contradiction:
Overlapping but different start times on the same day: penalize both by 0.15 unless one is Tier A and <14 days old, then penalize only the older.
Final confidence per atomic field = σ(sum - penalties).
Thresholds:
≥ 0.85 publish as “confirmed.”
0.65–0.85 publish but mark “provisional” and schedule a VoiceVerify.
< 0.65 hold for human or skip.
9) The “phone bot” is your unfair advantage
Most competitors won’t call. You should. A 20-second call resolves 80% of conflicts. Store call transcript and a short signed attestation: “Dana, bartender, 2025-09-01, confirmed M–F 3–6, bar only.”
Weight that highly but let it decay fast (14–21 days), because staff often give yesterday’s rules.

10) Build this without painting yourself into a corner
Data layer
Postgres + PostGIS for venues and schedules.
A simple “facts” table: (venue_id, field_path, value_jsonb, source, observed_at, trust, specificity, hash, evidence_url, snippet).
Event log of every extraction. You can replay consensus fast.
Workflow
Temporal.io or simple Celery/Sidekiq queues: one job per agent per venue.
Playwright cluster for headless fetch + OCR pipeline.
GPT-5 in strict JSON mode for extraction only; absolutely no generative guessing.
Guardrails
Reject any agent output that has unrecognized fields or fails schema validation.
Hard-fail if “status: active” arrives with zero schedule windows.
RAG is optional here. You want extract-and-score, not summarize. Use embeddings to de-dupe evidence and cluster near-identical claims.
11) Brutal pitfalls you’re probably underestimating
Instagram comments are a minefield; staff change and replies age out. Treat them as hints unless they’re <14 days and from the official account.
Yelp review counts are huge, but programmatic review access is rate-limited and plan-gated. Don’t architect around “infinite Yelp text.” 
docs.developer.yelp.com
+1
PDFs and Stories with tiny text will nuke OCR quality. Budget for a real OCR stack with image cleanup.
Game-day exceptions and holiday blackouts are the main reason consumers say “this app is wrong.” Put real effort into exceptions.
Names collide. “The Local” exists in half the cities in America. Phone and website are your unique keys.
12) MVP → v2 rollout
MVP (2–3 weeks)
Agents: Site, Google, Yelp, Instagram, VoiceVerify.
OCR + temporal parser + consensus scoring.
JSON contract with provenance and per-field confidence.
CLI and small dashboard for human review.
V2
Add Resy/Resy-like, Untappd/BeerMenus, Facebook, TikTok, Editorial.
Change detection watchers.
Conflict explanations in UI (“We chose 3–6pm because owner post on Aug 20 outweighed two older Yelp mentions.”)
Coverage metrics by city, freshness heatmap, precision audits.
KPIs
Precision@field for hours, areas, and pricing (target 95% for hours).
Median evidence age.
% of venues with voice confirmation in last 30 days.
% of fields flagged to human (push under 10%).
13) What your agents should return (minimum evidence discipline)
Every claim must include:
observed_at UTC
source_url or call_recording_id
snippet or ocr_text
modality and specificity
If you can’t meet that, the agent must return could_not_find. Your deterministic judge can’t fix a lack of receipts.
14) Where to start today
Write the JSON schema and validators.
Build SiteAgent + OCR + temporal parser.
Wire GoogleAgent Q&A/Posts and YelpAgent via Fusion API. 
BrightLocal
docs.developer.yelp.com
Implement the consensus function exactly as above with tunable weights.
Add the Phone bot. Watch your error rate plummet.
Do this and you’ll have the only happy-hour engine with real provenance and freshness instead of rumor-as-data.
Light citations about platforms I referenced
Google Business Profile Q&A and posts are owner-visible and public; Q&A is often used to clarify hours. 
BrightLocal
Google Help
Yelp Fusion exposes business and review endpoints, with access levels and limits.
docs.developer.yelp.com
+2
docs.developer.yelp.com
+2
Resy is a reservation/restaurant OS that includes event and marketing features that venues control.
Resy
+1
Popmenu is a restaurant website/menu platform that replaces PDFs with interactive menus.
get.popmenu.com
+1
Untappd for Business and BeerMenus power live drink menus and specials, which often include HH promotions. 
Untappd for Business™
+1
BeerMenus
If you want, I’ll convert this into a repo plan with table DDLs, agent interfaces, and a first pass at the consensus scoring code you can drop into your stack.
You said:
so how should we set this up technicalyl so that it can receive either one off restaurant lookup requests, or someone can build a list of requests by searching our restaurant list and then clicking multiple to add to a bulk request, or we should be able to upload bulk files of restaurants with various kinds of data in different structures and the system should be able to parse those into usable units that fit into our restaurant list determinstic structure -- do you see what im trying to do here? and i want to organize the tech stack so that it makes perfect sense and uses the most efficient amount of resources to get the best return with the most confident data
ChatGPT said:

Thought for 21s
I get it. You want one engine that can handle:
a single ad-hoc venue lookup,
selecting many venues from your own list for a bulk run, and
dropping in a messy CSV/XLSX/JSON from anywhere and still getting clean, confident HH data out.
Here’s the clean, scalable way to do it without wasting compute or painting yourself into a corner.
The shape of the system (one abstraction for all entry points)
Core concept: everything becomes a JobGroup with many JobItems.
A one-off lookup = JobGroup with 1 JobItem.
A multi-select from your list = JobGroup with N JobItems you queued from search.
A bulk upload = JobGroup produced by parsing a file into N canonical JobItems.
Every JobItem always contains a Canonical Restaurant Input (CRI) that your agents can trust:
{
  "name": "The Waterfront Bar & Grill",
  "address": "2044 Kettner Blvd, San Diego, CA 92101",
  "phone_e164": "+16195551212",
  "website": "https://waterfrontbarandgrill.com",
  "lat": 32.72421,
  "lng": -117.16915,
  "platform_ids": {
    "google_place_id": "ChIJ…",
    "yelp_business_id": "waterfront-san-diego",
    "instagram": "@waterfrontbar",
    "opentable_slug": "…"
  },
  "extra_hints": { "neighborhood": "Little Italy" }
}
If you don’t have that data up front, the Resolver builds it deterministically from whatever garbage the user provided (file columns, partial names, etc.) and either finds a strong match or flags it.
High-level architecture (modular, cheap, and obvious)
Frontend & APIs
Frontend: Next.js 15 + TypeScript. UX supports:
Search → multi-select → “Add to batch”.
One-off form (“paste a name or URL”).
Bulk upload (CSV/XLSX/JSON). Inline field-mapper when columns are unknown.
API gateway: Fastify (Node) or FastAPI (Python). Keep request/response tight; everything async.
Core services
Ingestion Service
Accepts one-offs, multi-select, and file uploads.
Normalizes to CRI via the Resolver.
Outputs a JobGroup and JobItems (status: queued).
Resolver (Entity Resolution & Canonicalizer)
Cleanses text (case/whitespace), parses addresses (libpostal), normalizes phones, geocodes if missing.
Queries your Venue Registry (Postgres + PostGIS) and external lookups (Places/Yelp if allowed) to attach platform IDs.
Scoring features: name similarity, phone exact match, address number/street match, domain root match, lat/lng proximity.
Deterministic thresholds:
score >= 0.9: auto-attach
0.75–0.9: needs human confirm
< 0.75: reject to review queue
Orchestrator (Workflow Engine)
Temporal.io (recommended). Each JobItem runs the same workflow:
resolve → plan agents → fetch (rate-limited) → extract → consolidate → consensus → store result → notify.
Gives you retries, timeouts, idempotency, and visibility by default.
Agent Runner Cluster
Containers with Playwright for headless fetch, plus HTTP fetchers for official APIs.
OCR sidecar (tesseract + image pre-processing or PaddleOCR).
LLM Extractor (GPT-5 structured output) enforces your JSON mini-schemas per source.
Strict rate limiter + per-domain budget, exponential backoff, and a grouped crawl strategy to reuse sessions per domain.
Consensus Engine (Deterministic Judge)
Consumes per-field claims + evidence and calculates your confidence with source weights, recency decay, specificity bonuses, and contradiction penalties.
Returns final HappyHourRecord + per-atom confidence + needs_review flags.
Data Stores
Postgres + PostGIS: venue registry, job state, final HH records, provenance.
Object storage (S3/GCS): raw HTML snapshots, PDFs, images, call recordings, OCR text.
Search index: Meilisearch or OpenSearch to power “pick many restaurants” and fuzzy lookup.
Queue: Temporal task queues (no extra Kafka unless you really need it later).
Observability
OpenTelemetry for traces, Prometheus metrics on per-agent cost/latency/success, Loki for logs.
Dashboards: “cost per JobItem,” “success rate by source,” “median evidence age,” “flag rate by field.”
Review Console
A small back-office UI: conflict diffs, listen to call clip, see screenshots, one-click accept/override.
Everything you approve becomes training data for threshold tuning.
Data contracts that keep you sane
Canonical Restaurant Input (CRI) – minimal but strict.
Must pass validation before any agent runs.
Populated by Resolver or directly by user if complete.
Agent Claim – every field has receipts:
{
  "field_path": "happy_hour.schedule.weekly.mon[0]",
  "value": {"start":"15:00","end":"18:00"},
  "source": "instagram_comment",
  "source_url": "https://instagram.com/p/…",
  "observed_at": "2025-09-01T23:04:00Z",
  "specificity": "exact_time_window",
  "modality": "text|image_ocr|voice",
  "agent_confidence": 0.82,
  "snippet": "Happy hour M–F 3–6, bar only."
}
HappyHourRecord (Final)
Your public JSON contract with status, schedule, offers, fine_print, and provenance.fields[*].confidence/evidence/conflicts.
Everything gets validated by Zod/JSON Schema in the API layer and again in the workflow to kill drift.
Bulk uploads without pain
Accepted inputs: CSV, TSV, XLSX, JSONL.
Parser pipeline:
Sniff delimiter/encoding. Convert to Arrow/Parquet in memory.
Column classifier maps unknown headers to CRI fields. Do it hybrid:
Rules first (exact matches like phone, tel, e164, website, url, addr, street, name).
ML second for weird ones (e.g., “biz_phone”, “venue_url”, “gplace”).
Interactive mapper (if confidence < 0.9 for any field) — show a 30-second UI to drag/drop columns to fields and save the mapping template by org.
Row-level validation; produce RowIssues for empty names, invalid phones, nonsense addresses.
Resolver runs to attach platform IDs (your biggest accuracy boost).
Emit a JobGroup with N JobItems.
Idempotency
source_doc_hash + row_index as a deterministic key. Re-uploads with the same key override or merge.
De-dupe
If your registry already has the venue and the same day’s HH record with equal or higher confidence, skip heavy crawling unless you have a recency trigger.
Multi-select from your list (the “cart” model)
Search service: query by name, city, tags, freshness, platform IDs.
Multi-select adds Venue IDs to a Selection object (like a shopping cart).
“Create JobGroup from Selection” spawns JobItems with existing CRIs and short-circuits Resolver.
Why this is cheap: you’re not re-resolving entities you already know, and you can schedule during off-peak or group by domain to reuse sessions.
Orchestration flow (per JobItem)
JobItemWorkflow:
  1. Load/Resolve CRI (skip if known good)
  2. Plan sources (Website + GBP + Yelp + Instagram + [others])
  3. Crawl/Fetch (respect budgets/rate limits; reuse sessions per domain)
  4. Extract → Agent Claims (strict JSON only)
  5. QA guards (temporal sanity, image/HH co-location, unit sanity)
  6. Consensus Engine → Final HH Record + per-atom confidence
  7. Persist + Emit events (webhooks/UI updates)
  8. If ambiguous → enqueue VoiceVerify substask
Budgets & cost control
Token bucket per source and per org.
Domain grouping (crawl menu site once, extract for multiple venues).
Dynamic plan: if Website already gives high-confidence fresh schedule, skip heavier sources.
Hard ceiling per JobItem; move anything over budget to needs_review.
Minimal schema (DDL you can paste)
-- Venues (registry)
create table venues (
  id uuid primary key,
  name text not null,
  address text,
  city text,
  state text,
  postal_code text,
  country text default 'US',
  phone_e164 text,
  website text,
  geom geometry(Point, 4326),
  platform_ids jsonb,         -- {google_place_id, yelp_business_id, ...}
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Job groups and items
create table job_groups (
  id uuid primary key,
  org_id uuid not null,
  created_by uuid,
  source text,                -- 'oneoff' | 'multiselect' | 'upload'
  label text,
  created_at timestamptz default now(),
  status text default 'queued'  -- queued|running|succeeded|failed|partial
);

create table job_items (
  id uuid primary key,
  job_group_id uuid references job_groups(id),
  venue_id uuid references venues(id),
  cri jsonb not null,
  status text default 'queued',
  started_at timestamptz,
  finished_at timestamptz,
  cost_cents int default 0,
  error text
);

-- Raw evidence (immutable)
create table claims (
  id uuid primary key,
  job_item_id uuid references job_items(id),
  venue_id uuid references venues(id),
  field_path text not null,
  value jsonb not null,
  source text not null,
  source_url text,
  observed_at timestamptz not null,
  specificity text,
  modality text,
  agent_confidence real,
  snippet text,
  created_at timestamptz default now()
);

-- Final records (latest active)
create table happy_hour_records (
  id uuid primary key,
  venue_id uuid references venues(id),
  compiled_at timestamptz not null,
  payload jsonb not null,   -- the final HH JSON
  version int default 1
);

-- Per-atom provenance and confidence (optional denormalized)
create table hh_field_provenance (
  id uuid primary key,
  record_id uuid references happy_hour_records(id),
  field_path text not null,
  confidence real not null,
  evidence_ids uuid[] not null,
  conflicts jsonb
);
APIs you actually need (clean and boring)
POST /ingest/oneoff → {input:{name|url|phone|address}} → JobGroupId
POST /ingest/upload → file → UploadId → mapping step → JobGroupId
GET /venues/search?q=… → paginated results for multi-select
POST /selections + POST /selections/{id}/add + POST /selections/{id}/run → JobGroupId
GET /job-groups/{id} → status + counts
GET /job-items/{id} → traces + evidence
GET /venues/{id}/happy-hour → latest HH JSON
Webhooks: job_group.completed, job_item.needs_review, venue.updated
Tech choices (opinionated and practical)
API/Orchestrator language: TypeScript across the board or Python across the board. Don’t split unless you must; Temporal has great SDKs for both.
Workflow: Temporal.io (massive win vs DIY retries/timeouts).
Headless agents: Playwright in containers on ECS Fargate or K8s; scale to zero.
DB: Postgres 15 + PostGIS; psql + Drizzle ORM (TS) or SQLAlchemy (Py).
Search: Meilisearch first; easy to run and cheap.
Validation: Zod (TS) or Pydantic (Py) + JSON Schema. Reject on fail.
Metrics/Tracing: OpenTelemetry + Prometheus + Grafana.
Storage: S3 with lifecycle rules.
Auth/Multi-tenant: JWT + RLS in Postgres (if you’re comfortable) or simple org_id scoping.
Where you’ll blow time if you’re not careful
Entity resolution is the beast. Invest early: good thresholds, phone/website normalization, and a manual “Is this the right venue?” step for the ambiguous 10–15%.
Bulk column mapping always looks easy; it never is. Ship the interactive mapper in v1 so users fix it for you, then learn from their mappings.
Browser costs can run away. Group crawls by domain, cache static resources, and short-circuit when owner data is fresh and confident.
Over-calling LLMs. Use LLMs only to extract structured snippets from already-targeted content. Don’t send entire pages if you can regex/DOM it first.
Rollout plan (fast, controlled)
Milestone 1 (1–2 weeks)
Venue registry + search.
One-off ingestion → Resolve → Website + Google agents only → Consensus → HH JSON.
Minimal job tracking + basic UI.
Milestone 2
Multi-select cart.
Bulk upload + interactive mapper.
Instagram + Yelp agents (respecting access limits), OCR pipeline.
Milestone 3
VoiceVerify agent + Review Console.
Freshness watchers + domain grouping.
Per-atom provenance/confidence displays in UI.
Cost dashboards and budgets.
Hit this shape and you’ll be efficient, confident, and adaptable. If you want, I’ll turn this into a repo scaffold with the DDL, Zod schemas, Temporal workflows, and a minimal agent runner so you can push a real v1 without wandering in circles.



ChatGPT can make mistakes. Check important info.
