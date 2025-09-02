# GPT-5 Happy Hour Discovery System - Ultimate Implementation Plan

## Project Vision
Transform the current GPT-5 happy hour system into the most powerful, accurate, and scalable restaurant intelligence platform by implementing a comprehensive multi-agent architecture with deterministic consensus scoring and evidence-based provenance tracking.

## Core Architecture: Universal Input → Unified Processing

### The "One Engine" Approach
Everything becomes a **JobGroup** containing **JobItems**:
- **Single lookup** = JobGroup with 1 JobItem
- **Multi-select** = JobGroup with N selected JobItems  
- **Bulk upload** = JobGroup with N parsed JobItems

### Canonical Restaurant Input (CRI)
Every restaurant becomes a standardized entity before processing:
```json
{
  "name": "The Waterfront Bar & Grill",
  "address": "2044 Kettner Blvd, San Diego, CA 92101",
  "phone_e164": "+16195551212", 
  "website": "https://waterfrontbarandgrill.com",
  "lat": 32.72421,
  "lng": -117.16915,
  "platform_ids": {
    "google_place_id": "ChIJ...",
    "yelp_business_id": "waterfront-san-diego", 
    "instagram": "@waterfrontbar",
    "resy_slug": "...",
    "opentable_slug": "..."
  },
  "extra_hints": { "neighborhood": "Little Italy" }
}
```

## Five-Tier Source Strategy (Weight-Based)

### Tier A - Owner/Official Sources (Weight: 1.0)
- **Restaurant Websites**: Happy hour pages, PDFs, Popmenu/BentoBox menus
- **Google Business Profile**: Posts, Q&A, owner-managed attributes, menu links
- **Reservation Platforms**: Resy/OpenTable/SevenRooms/Tock event modules with HH mentions
- **VoiceVerify Agent**: 20-second phone calls with staff confirmation (KILLER FEATURE)
- **Owner Communications**: Email newsletters, RSS feeds, direct updates

### Tier B - High-Coverage User Generated (Weight: 0.5-0.85) 
- **Google Reviews/Q&A**: Time-stamped customer reports with HH keywords
- **Yelp Reviews/Photos**: Fusion API + programmatic access for business data
- **Facebook Pages**: Posts, events, owner responses to HH questions
- **Instagram**: Posts, Stories, Highlights, comment threads with staff replies
- **TikTok**: Geotagged content with happy hour mentions and corrections

### Tier C - Beverage Ecosystems (Weight: 0.7)
- **Untappd for Business**: Live drink menus with time-bound HH specials
- **BeerMenus**: Current tap lists and pricing updates
- **Local Brewery Collaborations**: Cross-promotional content and tap takeovers

### Tier D - Editorial/Deal Aggregators (Weight: 0.3)
- **Local Publications**: Eater, Thrillist, Time Out, alt-weeklies
- **Deal Sites**: Groupon, LivingSocial, local "$1 oysters" roundups  
- **Social Communities**: Reddit city subs, Discord foodie servers

### Tier E - Edge Signals (Weight: 0.2-0.4)
- **Online Ordering**: Toast/Square/ChowNow HH-labeled categories
- **Delivery Platforms**: DoorDash/Uber Eats promotional hints
- **Wayback Machine**: Historical policy changes ("was HH removed?")
- **Event Calendars**: City events affecting HH availability (First Fridays, game days)

## Specialized Agent Architecture

### Orchestrator System
Receives restaurant entity and fans out work to specialized agents:

### Agent Fleet (Newsroom-Style Specialists)
1. **SiteAgent**: Website crawling, PDF processing, OCR for menu images
2. **GoogleAgent**: Business Profile scraping, Posts/Q&A extraction, menu harvesting
3. **YelpAgent**: Fusion API integration, review analysis, photo metadata
4. **SocialAgents**: Instagram/Facebook/TikTok content extraction with comment analysis
5. **ReservationAgent**: Resy/OpenTable/SevenRooms event data mining
6. **BeverageAgent**: Untappd/BeerMenus live menu tracking and specials
7. **OrderingAgent**: Toast/Square/ChowNow HH category scanning
8. **EditorialAgent**: Blog/publication scraping with historical decay marking
9. **VoiceVerifyAgent**: Automated phone verification with recording/transcript

### Shared Extraction Pipeline
- **Text Normalizer**: Timezone resolution, phone/website standardization
- **NER Pipeline**: Items, prices, days, times, exclusions ("bar only", "not holidays")
- **Visual OCR**: Menu processing with image cleanup (tesseract + preprocessing)
- **Temporal Parser**: "Mon–Fri 3–6", "daily 9–close", "industry night Mondays"
- **Currency/DST Normalizers**: Business hours overlap validation

### Agent Evidence Requirements
Every agent returns strict JSON with evidence pack:
```json
{
  "field_path": "happy_hour.schedule.weekly.mon[0]",
  "value": {"start":"15:00","end":"18:00"},
  "source": "instagram_comment", 
  "source_url": "https://instagram.com/p/...",
  "observed_at": "2025-09-01T23:04:00Z",
  "snippet": "Happy hour M–F 3–6! Bar only.",
  "specificity": "exact_time_window",
  "modality": "text|image_ocr|voice",
  "agent_confidence": 0.82
}
```

## Mathematical Consensus Engine

### Truth-Finding Algorithm (Deterministic, No "Vibes")
For each candidate value `v` for field `F`:

```
support(v) = Σᵢ [w_source(i) × w_time(i) × s_specificity(i) × s_agent(i)]
score(v) = σ(support(v) - contradiction_penalty(v))
```

### Recency Decay Formula  
```
w_time = exp(-age_days / half_life)
```
- **Standard venues**: 30-day half-life
- **Sports bars**: 7-day half-life (game day changes)
- **Vegas/tourist areas**: 3-day half-life (frequent updates)

### Source Weight Matrix
```
Website/Owner/VoiceConfirm: 1.0
Google Post/Q&A (owner): 0.85  
Reservation platforms: 0.75
Untappd/BeerMenus live: 0.7
Google/Yelp reviews: 0.5 (+0.1 if exact time/price)
Editorial/blogs: 0.3
```

### Specificity Bonuses
- **Exact time window**: 1.2×
- **Price with currency**: 1.15×
- **Staff-authored**: 1.1×
- **Vague ("afternoon")**: 0.8×

### Confidence Thresholds & Actions
- **≥ 0.85**: Publish as "confirmed" 
- **0.65–0.85**: Mark "provisional", schedule VoiceVerify
- **< 0.65**: Hold for human review or skip

### Element-Level Scoring
Score per atomic field: Monday window vs Tuesday window vs "bar-only" vs "$1 off drafts"

## Battle-Tested JSON Contract

### Final Happy Hour Record
```json
{
  "venue": {
    "name": "The Example",
    "address": "123 A St, San Diego, CA 92101",
    "phone": "+1-619-555-1212",
    "website": "https://example.com", 
    "timezone": "America/Los_Angeles",
    "platform_ids": {
      "google_place_id": "...",
      "yelp_business_id": "...",
      "resy_slug": "...",
      "instagram": "@examplebar"
    }
  },
  "happy_hour": {
    "status": "active|unknown|discontinued",
    "schedule": {
      "weekly": {
        "mon": [{"start":"15:00","end":"18:00"}],
        "tue": [{"start":"15:00","end":"18:00"}],
        "wed": [{"start":"15:00","end":"18:00"}], 
        "thu": [{"start":"15:00","end":"18:00"}],
        "fri": [{"start":"15:00","end":"18:00"}],
        "sat": [],
        "sun": []
      },
      "blackouts": [
        {"rule":"closed_holidays"},
        {"rule":"no_hh_on_home_games","notes":"Padres game days"}
      ],
      "areas": ["bar_only","patio_ok"],
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
          {"source":"website","url":"...","observed_at":"..."},
          {"source":"google_post","url":"...","observed_at":"..."},
          {"source":"instagram_comment","url":"...","observed_at":"..."}
        ],
        "conflicts": [
          {"value":{"start":"16:00","end":"18:00"},"source":"yelp_review","observed_at":"..."}
        ]
      }
    }
  },
  "qa": {
    "could_not_find": ["blackouts[1] exact list"],
    "needs_review": ["areas"],
    "notes_for_human": "IG says 'bar only'; website ambiguous."
  }
}
```

## Technical Stack Architecture

### Frontend (Next.js 15 + TypeScript)
- **Search Interface**: Multi-select restaurant discovery
- **One-off Form**: "Paste name or URL" quick lookup  
- **Bulk Upload**: CSV/XLSX/JSON with interactive column mapping
- **Review Console**: Conflict resolution, call playback, screenshot review

### API Layer (FastAPI Python)
```
POST /ingest/oneoff → {input:{name|url|phone}} → JobGroupId
POST /ingest/upload → file → UploadId → mapping → JobGroupId  
GET /venues/search?q=... → paginated results for multi-select
POST /selections + /selections/{id}/add + /selections/{id}/run → JobGroupId
GET /job-groups/{id} → status + counts
GET /job-items/{id} → traces + evidence
GET /venues/{id}/happy-hour → latest HH JSON
```

### Core Services Architecture
1. **Ingestion Service**: CRI normalization, file parsing
2. **Resolver**: Entity resolution with confidence scoring  
3. **Orchestrator**: Temporal.io workflow management
4. **Agent Runner**: Playwright cluster + OCR pipeline
5. **Consensus Engine**: Mathematical confidence calculation
6. **Review System**: Human verification workflow

### Data Architecture (PostgreSQL + PostGIS)
```sql
-- Venue registry
CREATE TABLE venues (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  address TEXT, 
  city TEXT,
  state TEXT,
  postal_code TEXT,
  country TEXT DEFAULT 'US',
  phone_e164 TEXT,
  website TEXT,
  geom GEOMETRY(Point, 4326),
  platform_ids JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Job management
CREATE TABLE job_groups (
  id UUID PRIMARY KEY,
  org_id UUID NOT NULL,
  created_by UUID,
  source TEXT, -- 'oneoff' | 'multiselect' | 'upload'
  label TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  status TEXT DEFAULT 'queued' -- queued|running|succeeded|failed|partial
);

CREATE TABLE job_items (
  id UUID PRIMARY KEY,
  job_group_id UUID REFERENCES job_groups(id),
  venue_id UUID REFERENCES venues(id),
  cri JSONB NOT NULL,
  status TEXT DEFAULT 'queued',
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  cost_cents INT DEFAULT 0,
  error TEXT
);

-- Evidence storage (immutable)
CREATE TABLE claims (
  id UUID PRIMARY KEY,
  job_item_id UUID REFERENCES job_items(id),
  venue_id UUID REFERENCES venues(id),
  field_path TEXT NOT NULL,
  value JSONB NOT NULL,
  source TEXT NOT NULL,
  source_url TEXT,
  observed_at TIMESTAMPTZ NOT NULL,
  specificity TEXT,
  modality TEXT,
  agent_confidence REAL,
  snippet TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Final records
CREATE TABLE happy_hour_records (
  id UUID PRIMARY KEY,
  venue_id UUID REFERENCES venues(id),
  compiled_at TIMESTAMPTZ NOT NULL,
  payload JSONB NOT NULL, -- final HH JSON
  version INT DEFAULT 1
);

-- Per-field provenance (denormalized)
CREATE TABLE hh_field_provenance (
  id UUID PRIMARY KEY,
  record_id UUID REFERENCES happy_hour_records(id),
  field_path TEXT NOT NULL,
  confidence REAL NOT NULL,
  evidence_ids UUID[] NOT NULL,
  conflicts JSONB
);
```

## Workflow Orchestration (Temporal.io)

### JobItem Workflow
```
1. Load/Resolve CRI (skip if known good)
2. Plan sources (Website + GBP + Yelp + Instagram + [others])  
3. Crawl/Fetch (respect budgets/rate limits; domain grouping)
4. Extract → Agent Claims (strict JSON only)
5. QA Guards (temporal sanity, image/HH co-location, unit checks)
6. Consensus Engine → Final HH Record + per-atom confidence
7. Persist + Emit events (webhooks/UI updates)
8. If ambiguous → enqueue VoiceVerify subtask
```

## Bulk Upload Intelligence

### File Processing Pipeline
1. **Sniff Format**: CSV, TSV, XLSX, JSONL auto-detection
2. **Column Classification**: 
   - Rules first: exact matches (phone, tel, website, addr, name)
   - ML second: fuzzy matches ("biz_phone", "venue_url")
3. **Interactive Mapper**: Drag/drop UI for < 0.9 confidence fields
4. **Row Validation**: Empty names, invalid phones, nonsense addresses
5. **Resolver**: Entity resolution to attach platform IDs
6. **JobGroup Creation**: Emit N JobItems with CRIs

### Idempotency & Deduplication
- **Key**: `source_doc_hash + row_index` 
- **De-dupe**: Skip if venue has same-day HH record with equal/higher confidence
- **Smart Re-processing**: Only trigger on recency/confidence thresholds

## Adversarial Quality Assurance

### Automated Validation Checks
- **Temporal Coherence**: Don't accept "Mon–Fri 3–6" if venue closed at 3pm Tuesday
- **Geographic Validation**: "Bar only" venues must actually have bars
- **Unit Sanity**: Flag $0 oysters, $50 well drinks
- **OCR Cross-check**: Times must appear near "Happy Hour" in same image
- **Name Collision**: Verify correct venue via phone/website/lat-lng

### Contradiction Detection
- **Overlapping Conflicts**: Different start times same day
- **Penalty System**: Proportional to conflict closeness
- **Resolution Priority**: Newer + owner-authored wins (within 45 days)

### Human Review Triggers
- Data completeness < 60%
- Conflicting sources
- < 2 evidence sources
- High-value venue discrepancies

## VoiceVerify Agent (Unfair Advantage)

### 20-Second Decision Tree
```
"Do you currently offer happy hour?"
"Which days and what times?" 
"Bar only or full restaurant?"
"Any exclusions, game days, holidays?"
```

### Evidence Capture
- **Recording + Transcript**: Full call audio with consent
- **Attestation**: "Dana, bartender, 2025-09-01, confirmed M–F 3–6, bar only"
- **High Trust**: Weight 1.0 but fast decay (14-21 days)
- **Conflict Resolution**: 80% of conflicts resolved by single call

## Change Detection & Freshness

### Watcher Systems
- **Website**: Hash HH section/PDF, detect changes
- **Instagram**: Subscribe to posts with "happy" or clock emojis
- **Google Q&A**: Poll for answers containing "hour", "happy", times, prices
- **BeerMenus/Untappd**: Monitor menu revisions

### Trigger Conditions
- New evidence arrives
- User reports incorrect info  
- VoiceVerify fails twice
- Scheduled freshness check

## Cost Optimization Strategy

### Intelligent Resource Management
- **Dynamic Planning**: Skip redundant sources for high-confidence data
- **Domain Grouping**: Reuse browser sessions across venues
- **Token Budgets**: Hard limits per venue analysis
- **Off-peak Scheduling**: Bulk jobs during low-cost periods

### Agent Cost Control
- **Cascade Logic**: If website gives high-confidence fresh data, skip heavy sources
- **Budget Ceiling**: Move over-budget items to needs_review
- **Session Reuse**: Group crawls by domain to minimize browser overhead

## Implementation Roadmap

### Milestone 1: Foundation (Weeks 1-2)
- **Venue Registry**: PostgreSQL + search index
- **Basic Agents**: Site, Google, Yelp, VoiceVerify
- **Simple Consensus**: Basic confidence scoring
- **One-off Ingestion**: Single restaurant lookup

### Milestone 2: Multi-Source (Weeks 3-4) 
- **Agent Expansion**: Instagram, Facebook, OCR pipeline
- **Bulk Upload**: CSV/XLSX processing with column mapper
- **Multi-select**: Shopping cart interface
- **Enhanced Consensus**: Contradiction detection

### Milestone 3: Intelligence (Weeks 5-6)
- **Full Agent Fleet**: TikTok, Editorial, Reservation platforms
- **Review Console**: Human verification workflow  
- **Change Detection**: Freshness watchers
- **Quality Metrics**: Precision tracking, false positive detection

### Milestone 4: Scale (Weeks 7-8)
- **Performance**: Domain grouping, session reuse
- **Advanced Features**: Per-atom provenance display
- **Cost Dashboards**: Budget monitoring, optimization alerts
- **API Hardening**: Rate limiting, comprehensive error handling

## Success Metrics & KPIs

### Accuracy Targets
- **Field Precision**: 95% for hours, 90% for pricing
- **False Positive Rate**: < 5% incorrect confirmations
- **Human Review Rate**: < 10% requiring intervention
- **Voice Verification**: 30% of venues confirmed monthly

### Performance Goals
- **Response Time**: < 2s search, < 30s analysis
- **Cost Efficiency**: < $0.05 per comprehensive analysis
- **Coverage**: 95% evidence freshness < 7 days
- **Reliability**: 99.5% system uptime

### Business Metrics
- **Data Coverage**: 10,000+ verified venues
- **API Adoption**: 100+ developer integrations
- **User Satisfaction**: 90% accuracy rating
- **Revenue Growth**: $50k ARR within 6 months

## Risk Mitigation

### Technical Risks
- **Rate Limits**: Intelligent queuing, exponential backoff
- **API Changes**: Fallback compatibility, graceful degradation
- **Cost Overruns**: Hard budget limits, real-time monitoring
- **Legal Compliance**: ToS respect, partnership development

### Operational Risks  
- **Entity Resolution**: Manual review queue for ambiguous matches
- **OCR Quality**: Image preprocessing, multi-engine approach
- **Data Quality**: Multi-source verification, confidence thresholds
- **Scalability**: Horizontal architecture from day one

## Competitive Advantages

### Unique Value Propositions
1. **Mathematical Consensus**: Only platform with deterministic confidence scoring
2. **VoiceVerify**: Automated phone verification (competitors won't call)
3. **Evidence Provenance**: Complete audit trail for every data point
4. **Multi-modal Intelligence**: Text + OCR + voice + structured data
5. **Real-time Freshness**: Change detection with automatic updates

### Market Positioning
- **Developers**: Reliable API with confidence scores and evidence trails
- **Enterprises**: White-label solution with custom requirements
- **Consumers**: Most accurate and up-to-date happy hour information
- **Restaurants**: Direct update portal with performance analytics

---

## Next Actions (Start Today)

### Immediate (This Week)
1. **JSON Schema**: Write validators for CRI and HappyHourRecord
2. **Database**: Set up PostgreSQL with initial table structure  
3. **SiteAgent**: Build with OCR + temporal parser
4. **Consensus Engine**: Implement mathematical scoring model

### Short Term (Next 2 Weeks)
1. **Google/Yelp Agents**: Wire up Business Profile + Fusion API
2. **VoiceVerify**: Build phone bot with recording capability
3. **Basic UI**: One-off lookup form with results display
4. **Temporal Setup**: Workflow orchestration infrastructure

### Medium Term (Next Month)
1. **Bulk Upload**: File processing with column mapper
2. **Multi-select**: Shopping cart restaurant selection
3. **Social Agents**: Instagram/Facebook content extraction
4. **Review Console**: Human verification workflow

**This transforms your GPT-5 happy hour system into the definitive restaurant intelligence platform with provenance, freshness, and mathematical confidence instead of rumor-as-data.**

*Built with GPT-5's Advanced Reasoning | Evidence-Based Truth Finding | Deterministic Confidence Scoring*