-- GPT-5 Happy Hour Discovery System - MVP+ Database Schema
-- Optimized for Supabase with RLS and real-time capabilities

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- ============================================================================
-- CORE ENTITIES
-- ============================================================================

-- Venues: Canonical restaurant entities with platform IDs
CREATE TABLE venues (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    address TEXT,
    city TEXT,
    state TEXT,
    postal_code TEXT,
    country TEXT DEFAULT 'US',
    phone_e164 TEXT,
    website TEXT,
    
    -- Geographic data
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    geom GEOMETRY(Point, 4326),
    
    -- Platform identifiers for agent lookup
    platform_ids JSONB DEFAULT '{}',
    -- Example: {"google_place_id": "ChIJ...", "yelp_business_id": "venue-name", "instagram": "@venue"}
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID, -- For future multi-user support
    
    -- Search optimization
    search_vector TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('english', COALESCE(name, '') || ' ' || COALESCE(city, '') || ' ' || COALESCE(address, ''))
    ) STORED
);

-- Indexes for performance
CREATE INDEX venues_search_idx ON venues USING GIN(search_vector);
CREATE INDEX venues_geom_idx ON venues USING GIST(geom);
CREATE INDEX venues_city_idx ON venues(city);
CREATE INDEX venues_platform_ids_idx ON venues USING GIN(platform_ids);

-- Auto-update timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_venues_updated_at BEFORE UPDATE ON venues
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- JOB MANAGEMENT (Simplified - No Temporal.io)
-- ============================================================================

-- Analysis jobs: Track restaurant happy hour analysis requests
CREATE TABLE analysis_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    venue_id UUID REFERENCES venues(id) ON DELETE CASCADE,
    
    -- Job metadata
    status TEXT DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),
    source TEXT DEFAULT 'manual' CHECK (source IN ('manual', 'bulk_upload', 'api', 'scheduled')),
    priority INTEGER DEFAULT 5, -- 1 = highest, 10 = lowest
    
    -- Canonical Restaurant Input (what agents work with)
    cri JSONB NOT NULL,
    
    -- Execution tracking
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    
    -- Cost tracking
    cost_cents INTEGER DEFAULT 0,
    tokens_used INTEGER DEFAULT 0,
    agents_run TEXT[] DEFAULT '{}',
    
    -- Results
    final_confidence DECIMAL(3,2), -- 0.00 to 1.00
    needs_human_review BOOLEAN DEFAULT FALSE,
    review_reasons TEXT[],
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID
);

-- Indexes
CREATE INDEX analysis_jobs_status_idx ON analysis_jobs(status);
CREATE INDEX analysis_jobs_venue_idx ON analysis_jobs(venue_id);
CREATE INDEX analysis_jobs_created_idx ON analysis_jobs(created_at DESC);
CREATE INDEX analysis_jobs_priority_status_idx ON analysis_jobs(priority, status);

CREATE TRIGGER update_analysis_jobs_updated_at BEFORE UPDATE ON analysis_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- EVIDENCE & CLAIMS (Heart of the System)
-- ============================================================================

-- Agent claims: Raw evidence from each agent with full provenance
CREATE TABLE agent_claims (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES analysis_jobs(id) ON DELETE CASCADE,
    venue_id UUID REFERENCES venues(id) ON DELETE CASCADE,
    
    -- Evidence metadata
    agent_name TEXT NOT NULL, -- 'SiteAgent', 'GoogleAgent', 'VoiceVerifyAgent', etc.
    source_type TEXT NOT NULL, -- 'website', 'google_post', 'yelp_review', 'phone_call', etc.
    source_url TEXT,
    source_domain TEXT, -- For grouping by reliability
    
    -- Field-specific claim
    field_path TEXT NOT NULL, -- 'schedule.weekly.mon[0]', 'offers[2].price', etc.
    field_value JSONB NOT NULL, -- The actual extracted value
    
    -- Evidence quality
    agent_confidence DECIMAL(3,2) NOT NULL, -- Agent's self-assessment (0.00-1.00)
    specificity TEXT CHECK (specificity IN ('exact', 'approximate', 'vague', 'implied')),
    modality TEXT CHECK (modality IN ('text', 'image_ocr', 'voice', 'structured_data')),
    
    -- Temporal data
    observed_at TIMESTAMPTZ NOT NULL, -- When this info was found/valid
    scraped_at TIMESTAMPTZ DEFAULT NOW(), -- When we extracted it
    
    -- Raw evidence
    raw_snippet TEXT, -- Original text/transcript that supports this claim
    raw_data JSONB, -- Full API response, HTML, etc. for debugging
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for consensus engine queries
CREATE INDEX agent_claims_job_idx ON agent_claims(job_id);
CREATE INDEX agent_claims_venue_field_idx ON agent_claims(venue_id, field_path);
CREATE INDEX agent_claims_source_type_idx ON agent_claims(source_type);
CREATE INDEX agent_claims_observed_at_idx ON agent_claims(observed_at DESC);
CREATE INDEX agent_claims_confidence_idx ON agent_claims(agent_confidence DESC);

-- ============================================================================
-- FINAL RESULTS (What Users See)
-- ============================================================================

-- Happy hour records: Final consensus results with confidence per field
CREATE TABLE happy_hour_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    venue_id UUID REFERENCES venues(id) ON DELETE CASCADE,
    job_id UUID REFERENCES analysis_jobs(id),
    
    -- Core happy hour data (structured JSON)
    status TEXT CHECK (status IN ('active', 'discontinued', 'unknown', 'no_happy_hour')),
    schedule JSONB, -- Weekly schedule with time slots
    offers JSONB, -- Array of drink/food specials
    areas JSONB, -- Where happy hour applies (bar, patio, etc.)
    blackouts JSONB, -- Game days, holidays, etc.
    fine_print TEXT[],
    
    -- Quality metrics
    overall_confidence DECIMAL(3,2) NOT NULL,
    completeness_score DECIMAL(3,2), -- How much of the schema we filled
    evidence_count INTEGER DEFAULT 0,
    source_diversity INTEGER DEFAULT 0, -- Number of different source types
    
    -- Freshness
    compiled_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ, -- When this data should be refreshed
    
    -- Human review
    needs_review BOOLEAN DEFAULT FALSE,
    reviewed_by UUID,
    reviewed_at TIMESTAMPTZ,
    review_status TEXT CHECK (review_status IN ('pending', 'approved', 'rejected', 'modified')),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Only one active record per venue at a time
CREATE UNIQUE INDEX happy_hour_records_venue_active_idx ON happy_hour_records(venue_id) 
WHERE review_status != 'rejected';

-- Indexes
CREATE INDEX happy_hour_records_venue_idx ON happy_hour_records(venue_id);
CREATE INDEX happy_hour_records_confidence_idx ON happy_hour_records(overall_confidence DESC);
CREATE INDEX happy_hour_records_compiled_idx ON happy_hour_records(compiled_at DESC);
CREATE INDEX happy_hour_records_needs_review_idx ON happy_hour_records(needs_review) WHERE needs_review = TRUE;

CREATE TRIGGER update_happy_hour_records_updated_at BEFORE UPDATE ON happy_hour_records
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- CONSENSUS TRACKING (Field-Level Confidence)
-- ============================================================================

-- Field confidence: Per-field confidence scores with evidence trail
CREATE TABLE field_confidence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    record_id UUID REFERENCES happy_hour_records(id) ON DELETE CASCADE,
    venue_id UUID REFERENCES venues(id) ON DELETE CASCADE,
    
    field_path TEXT NOT NULL,
    field_value JSONB NOT NULL,
    confidence DECIMAL(3,2) NOT NULL,
    
    -- Supporting evidence
    supporting_claim_ids UUID[],
    conflicting_claim_ids UUID[],
    
    -- Consensus algorithm details
    source_weight_sum DECIMAL(5,2),
    recency_weight_sum DECIMAL(5,2),
    specificity_bonus DECIMAL(3,2),
    contradiction_penalty DECIMAL(3,2),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX field_confidence_record_idx ON field_confidence(record_id);
CREATE INDEX field_confidence_venue_field_idx ON field_confidence(venue_id, field_path);

-- ============================================================================
-- BULK OPERATIONS
-- ============================================================================

-- Bulk uploads: Track CSV/file uploads
CREATE TABLE bulk_uploads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename TEXT NOT NULL,
    file_size INTEGER,
    mime_type TEXT,
    
    -- Processing status
    status TEXT DEFAULT 'uploaded' CHECK (status IN ('uploaded', 'parsing', 'processing', 'completed', 'failed')),
    total_rows INTEGER,
    processed_rows INTEGER DEFAULT 0,
    successful_rows INTEGER DEFAULT 0,
    failed_rows INTEGER DEFAULT 0,
    
    -- Column mapping (for CSV parsing)
    column_mapping JSONB,
    
    -- Results
    created_job_ids UUID[], -- Analysis jobs created from this upload
    error_log JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID
);

CREATE INDEX bulk_uploads_status_idx ON bulk_uploads(status);
CREATE INDEX bulk_uploads_created_idx ON bulk_uploads(created_at DESC);

CREATE TRIGGER update_bulk_uploads_updated_at BEFORE UPDATE ON bulk_uploads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SYSTEM METRICS & MONITORING
-- ============================================================================

-- Agent performance: Track agent success rates and costs
CREATE TABLE agent_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name TEXT NOT NULL,
    date DATE DEFAULT CURRENT_DATE,
    
    -- Performance metrics
    total_runs INTEGER DEFAULT 0,
    successful_extractions INTEGER DEFAULT 0,
    failed_extractions INTEGER DEFAULT 0,
    average_confidence DECIMAL(3,2),
    
    -- Cost metrics
    total_cost_cents INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    average_response_time_ms INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX agent_metrics_name_date_idx ON agent_metrics(agent_name, date);

-- System costs: Daily cost tracking
CREATE TABLE daily_costs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE DEFAULT CURRENT_DATE,
    
    -- Cost breakdown
    openai_cost_cents INTEGER DEFAULT 0,
    twilio_cost_cents INTEGER DEFAULT 0,
    aws_cost_cents INTEGER DEFAULT 0,
    total_cost_cents INTEGER DEFAULT 0,
    
    -- Usage metrics
    total_analyses INTEGER DEFAULT 0,
    total_phone_calls INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX daily_costs_date_idx ON daily_costs(date);

-- ============================================================================
-- ROW LEVEL SECURITY (Future Multi-Tenant Support)
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE venues ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE happy_hour_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE field_confidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE bulk_uploads ENABLE ROW LEVEL SECURITY;

-- Basic policies (allow all for MVP, restrict later)
CREATE POLICY "Allow all for service role" ON venues FOR ALL TO service_role;
CREATE POLICY "Allow all for service role" ON analysis_jobs FOR ALL TO service_role;
CREATE POLICY "Allow all for service role" ON agent_claims FOR ALL TO service_role;
CREATE POLICY "Allow all for service role" ON happy_hour_records FOR ALL TO service_role;
CREATE POLICY "Allow all for service role" ON field_confidence FOR ALL TO service_role;
CREATE POLICY "Allow all for service role" ON bulk_uploads FOR ALL TO service_role;

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to calculate venue confidence score
CREATE OR REPLACE FUNCTION calculate_venue_confidence(venue_uuid UUID)
RETURNS DECIMAL(3,2) AS $$
DECLARE
    avg_confidence DECIMAL(3,2);
BEGIN
    SELECT AVG(overall_confidence)
    INTO avg_confidence
    FROM happy_hour_records 
    WHERE venue_id = venue_uuid 
    AND review_status != 'rejected';
    
    RETURN COALESCE(avg_confidence, 0.00);
END;
$$ LANGUAGE plpgsql;

-- Function to get latest happy hour data for a venue
CREATE OR REPLACE FUNCTION get_latest_happy_hour(venue_uuid UUID)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'status', status,
        'schedule', schedule,
        'offers', offers,
        'areas', areas,
        'blackouts', blackouts,
        'fine_print', fine_print,
        'confidence', overall_confidence,
        'compiled_at', compiled_at,
        'expires_at', expires_at
    )
    INTO result
    FROM happy_hour_records
    WHERE venue_id = venue_uuid
    AND review_status != 'rejected'
    ORDER BY compiled_at DESC
    LIMIT 1;
    
    RETURN COALESCE(result, '{}'::jsonb);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SAMPLE DATA (For Testing)
-- ============================================================================

-- Insert some test venues (La Jolla restaurants from your current data)
INSERT INTO venues (name, address, city, state, phone_e164, website, latitude, longitude) VALUES
('DUKES RESTAURANT', '1216 PROSPECT ST, LA JOLLA, CA 92037', 'LA JOLLA', 'CA', '+18584545888', 'https://dukeslajolla.com', 32.8515, -117.2759),
('BARBARELLA RESTAURANT', '2171 AVENIDA DE LA PLAYA, LA JOLLA, CA 92037', 'LA JOLLA', 'CA', '+18584545001', null, 32.8511, -117.2756);

-- Update geom column from lat/lng
UPDATE venues SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326) 
WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View: Venues with their latest happy hour status
CREATE VIEW venues_with_happy_hour AS
SELECT 
    v.*,
    hr.status as happy_hour_status,
    hr.overall_confidence,
    hr.compiled_at as last_analyzed,
    hr.expires_at as data_expires,
    hr.needs_review
FROM venues v
LEFT JOIN happy_hour_records hr ON v.id = hr.venue_id 
    AND hr.review_status != 'rejected'
    AND hr.compiled_at = (
        SELECT MAX(compiled_at) 
        FROM happy_hour_records hr2 
        WHERE hr2.venue_id = v.id 
        AND hr2.review_status != 'rejected'
    );

-- View: Analysis queue (jobs waiting to run)
CREATE VIEW analysis_queue AS
SELECT 
    aj.*,
    v.name as venue_name,
    v.city as venue_city
FROM analysis_jobs aj
JOIN venues v ON aj.venue_id = v.id
WHERE aj.status = 'queued'
ORDER BY aj.priority ASC, aj.created_at ASC;

-- View: Agent performance summary
CREATE VIEW agent_performance AS
SELECT 
    agent_name,
    COUNT(*) as total_claims,
    AVG(agent_confidence) as avg_confidence,
    COUNT(DISTINCT venue_id) as venues_processed,
    MAX(created_at) as last_active
FROM agent_claims
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY agent_name
ORDER BY total_claims DESC;

COMMENT ON TABLE venues IS 'Canonical restaurant entities with platform IDs for agent lookup';
COMMENT ON TABLE analysis_jobs IS 'Track restaurant happy hour analysis requests and execution';  
COMMENT ON TABLE agent_claims IS 'Raw evidence from agents with full provenance tracking';
COMMENT ON TABLE happy_hour_records IS 'Final consensus results with field-level confidence';
COMMENT ON TABLE field_confidence IS 'Per-field confidence scores from consensus algorithm';