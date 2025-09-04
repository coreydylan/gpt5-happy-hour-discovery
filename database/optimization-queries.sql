-- Database Optimization Queries for GPT-5 Happy Hour Discovery
-- Performance improvements and maintenance queries

-- ============================================================================
-- ADDITIONAL INDEXES FOR PERFORMANCE OPTIMIZATION
-- ============================================================================

-- Composite indexes for common query patterns
CREATE INDEX CONCURRENTLY IF NOT EXISTS venues_city_state_idx ON venues(city, state);
CREATE INDEX CONCURRENTLY IF NOT EXISTS venues_name_city_idx ON venues(name, city);
CREATE INDEX CONCURRENTLY IF NOT EXISTS venues_updated_at_idx ON venues(updated_at DESC);

-- Analysis jobs optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS analysis_jobs_status_priority_created_idx 
    ON analysis_jobs(status, priority, created_at) 
    WHERE status IN ('queued', 'running');

CREATE INDEX CONCURRENTLY IF NOT EXISTS analysis_jobs_venue_status_idx 
    ON analysis_jobs(venue_id, status, created_at DESC);

-- Agent claims optimization for consensus queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS agent_claims_venue_field_confidence_idx 
    ON agent_claims(venue_id, field_path, agent_confidence DESC, observed_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS agent_claims_job_agent_idx 
    ON agent_claims(job_id, agent_name);

-- Happy hour records optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS happy_hour_records_status_confidence_idx 
    ON happy_hour_records(status, overall_confidence DESC) 
    WHERE status = 'active';

-- Partial indexes for common WHERE conditions
CREATE INDEX CONCURRENTLY IF NOT EXISTS agent_claims_recent_idx 
    ON agent_claims(venue_id, field_path, agent_confidence) 
    WHERE observed_at >= NOW() - INTERVAL '30 days';

-- ============================================================================
-- QUERY OPTIMIZATION FUNCTIONS
-- ============================================================================

-- Optimized venue search with full-text search
CREATE OR REPLACE FUNCTION search_venues_optimized(
    search_term TEXT,
    search_limit INTEGER DEFAULT 20,
    city_filter TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    name TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    phone_e164 TEXT,
    happy_hour_status TEXT,
    confidence DECIMAL(3,2),
    rank REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        v.id,
        v.name,
        v.address,
        v.city,
        v.state,
        v.phone_e164,
        hr.status as happy_hour_status,
        hr.overall_confidence as confidence,
        ts_rank(v.search_vector, plainto_tsquery('english', search_term)) as rank
    FROM venues v
    LEFT JOIN happy_hour_records hr ON v.id = hr.venue_id 
        AND hr.review_status != 'rejected'
        AND hr.compiled_at = (
            SELECT MAX(compiled_at) 
            FROM happy_hour_records hr2 
            WHERE hr2.venue_id = v.id 
            AND hr2.review_status != 'rejected'
        )
    WHERE 
        (v.search_vector @@ plainto_tsquery('english', search_term)
         OR v.name ILIKE '%' || search_term || '%')
        AND (city_filter IS NULL OR v.city ILIKE city_filter)
    ORDER BY 
        ts_rank(v.search_vector, plainto_tsquery('english', search_term)) DESC,
        v.name ASC
    LIMIT search_limit;
END;
$$ LANGUAGE plpgsql;

-- Optimized job queue query
CREATE OR REPLACE FUNCTION get_next_analysis_jobs(job_limit INTEGER DEFAULT 10)
RETURNS TABLE (
    id UUID,
    venue_id UUID,
    venue_name TEXT,
    cri JSONB,
    priority INTEGER,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        aj.id,
        aj.venue_id,
        v.name as venue_name,
        aj.cri,
        aj.priority,
        aj.created_at
    FROM analysis_jobs aj
    JOIN venues v ON aj.venue_id = v.id
    WHERE aj.status = 'queued'
    ORDER BY aj.priority ASC, aj.created_at ASC
    LIMIT job_limit
    FOR UPDATE SKIP LOCKED; -- Prevent concurrent processing of same job
END;
$$ LANGUAGE plpgsql;

-- Batch update job status
CREATE OR REPLACE FUNCTION update_job_status(
    job_ids UUID[],
    new_status TEXT,
    error_msg TEXT DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    affected_rows INTEGER;
BEGIN
    UPDATE analysis_jobs 
    SET 
        status = new_status,
        updated_at = NOW(),
        error_message = COALESCE(error_msg, error_message),
        started_at = CASE 
            WHEN new_status = 'running' AND started_at IS NULL THEN NOW() 
            ELSE started_at 
        END,
        completed_at = CASE 
            WHEN new_status IN ('completed', 'failed', 'cancelled') THEN NOW() 
            ELSE completed_at 
        END
    WHERE id = ANY(job_ids);
    
    GET DIAGNOSTICS affected_rows = ROW_COUNT;
    RETURN affected_rows;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- PERFORMANCE MONITORING FUNCTIONS
-- ============================================================================

-- Analyze table statistics
CREATE OR REPLACE FUNCTION analyze_table_stats()
RETURNS TABLE (
    table_name TEXT,
    row_count BIGINT,
    table_size TEXT,
    index_size TEXT,
    total_size TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        schemaname||'.'||tablename as table_name,
        n_tup_ins - n_tup_del as row_count,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as table_size,
        pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) as index_size,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) + pg_indexes_size(schemaname||'.'||tablename)) as total_size
    FROM pg_stat_user_tables 
    WHERE schemaname = 'public'
    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
END;
$$ LANGUAGE plpgsql;

-- Get slow queries (requires pg_stat_statements extension)
CREATE OR REPLACE FUNCTION get_slow_queries(limit_count INTEGER DEFAULT 10)
RETURNS TABLE (
    query TEXT,
    calls BIGINT,
    total_time DOUBLE PRECISION,
    mean_time DOUBLE PRECISION,
    rows BIGINT
) AS $$
BEGIN
    -- Check if pg_stat_statements is available
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements') THEN
        RAISE NOTICE 'pg_stat_statements extension not installed';
        RETURN;
    END IF;
    
    RETURN QUERY
    SELECT 
        pss.query,
        pss.calls,
        pss.total_exec_time as total_time,
        pss.mean_exec_time as mean_time,
        pss.rows
    FROM pg_stat_statements pss
    ORDER BY pss.mean_exec_time DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- MAINTENANCE PROCEDURES
-- ============================================================================

-- Clean up old data
CREATE OR REPLACE FUNCTION cleanup_old_data(days_to_keep INTEGER DEFAULT 90)
RETURNS TEXT AS $$
DECLARE
    deleted_claims INTEGER;
    deleted_jobs INTEGER;
    cleanup_date TIMESTAMPTZ;
    result_text TEXT;
BEGIN
    cleanup_date := NOW() - (days_to_keep || ' days')::INTERVAL;
    
    -- Delete old agent claims for completed jobs
    DELETE FROM agent_claims 
    WHERE job_id IN (
        SELECT id FROM analysis_jobs 
        WHERE status IN ('completed', 'failed') 
        AND completed_at < cleanup_date
    );
    GET DIAGNOSTICS deleted_claims = ROW_COUNT;
    
    -- Delete old completed/failed jobs
    DELETE FROM analysis_jobs 
    WHERE status IN ('completed', 'failed') 
    AND completed_at < cleanup_date;
    GET DIAGNOSTICS deleted_jobs = ROW_COUNT;
    
    result_text := format('Cleaned up %s old agent claims and %s old jobs older than %s days', 
        deleted_claims, deleted_jobs, days_to_keep);
    
    RETURN result_text;
END;
$$ LANGUAGE plpgsql;

-- Update table statistics
CREATE OR REPLACE FUNCTION update_table_statistics()
RETURNS TEXT AS $$
DECLARE
    table_rec RECORD;
    updated_count INTEGER := 0;
BEGIN
    -- Analyze all user tables
    FOR table_rec IN 
        SELECT schemaname, tablename 
        FROM pg_stat_user_tables 
        WHERE schemaname = 'public'
    LOOP
        EXECUTE 'ANALYZE ' || quote_ident(table_rec.schemaname) || '.' || quote_ident(table_rec.tablename);
        updated_count := updated_count + 1;
    END LOOP;
    
    RETURN format('Updated statistics for %s tables', updated_count);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- MONITORING VIEWS
-- ============================================================================

-- Active job monitoring
CREATE OR REPLACE VIEW active_jobs_summary AS
SELECT 
    status,
    COUNT(*) as job_count,
    MIN(created_at) as oldest_job,
    MAX(created_at) as newest_job,
    AVG(EXTRACT(EPOCH FROM (NOW() - created_at))) as avg_age_seconds
FROM analysis_jobs
WHERE status IN ('queued', 'running')
GROUP BY status;

-- Database size monitoring
CREATE OR REPLACE VIEW database_size_summary AS
SELECT 
    'Total Database Size' as metric,
    pg_size_pretty(pg_database_size(current_database())) as value
UNION ALL
SELECT 
    'Total Table Size' as metric,
    pg_size_pretty(sum(pg_total_relation_size(schemaname||'.'||tablename))) as value
FROM pg_stat_user_tables 
WHERE schemaname = 'public'
UNION ALL
SELECT 
    'Total Index Size' as metric,
    pg_size_pretty(sum(pg_indexes_size(schemaname||'.'||tablename))) as value
FROM pg_stat_user_tables 
WHERE schemaname = 'public';

-- Index usage monitoring
CREATE OR REPLACE VIEW index_usage_stats AS
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as times_used,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- ============================================================================
-- OPTIMIZATION RECOMMENDATIONS
-- ============================================================================

-- Function to get optimization recommendations
CREATE OR REPLACE FUNCTION get_optimization_recommendations()
RETURNS TABLE (
    category TEXT,
    recommendation TEXT,
    priority TEXT,
    impact TEXT
) AS $$
BEGIN
    RETURN QUERY
    -- Unused indexes
    SELECT 
        'Index Optimization'::TEXT as category,
        'Consider dropping unused index: ' || indexname as recommendation,
        'Medium'::TEXT as priority,
        'Reduce storage and maintenance overhead'::TEXT as impact
    FROM pg_stat_user_indexes 
    WHERE idx_scan = 0 
    AND schemaname = 'public'
    
    UNION ALL
    
    -- Large tables without recent analysis
    SELECT 
        'Table Maintenance'::TEXT as category,
        'Run ANALYZE on table: ' || schemaname||'.'||tablename as recommendation,
        'High'::TEXT as priority,
        'Improve query planning'::TEXT as impact
    FROM pg_stat_user_tables 
    WHERE (last_analyze IS NULL OR last_analyze < NOW() - INTERVAL '7 days')
    AND n_tup_ins + n_tup_upd + n_tup_del > 1000
    AND schemaname = 'public'
    
    UNION ALL
    
    -- Tables with high update/delete ratio
    SELECT 
        'Table Maintenance'::TEXT as category,
        'Consider VACUUM FULL on table: ' || schemaname||'.'||tablename as recommendation,
        'Medium'::TEXT as priority,
        'Reclaim dead tuple space'::TEXT as impact
    FROM pg_stat_user_tables 
    WHERE n_dead_tup::FLOAT / GREATEST(n_live_tup, 1) > 0.1
    AND n_dead_tup > 1000
    AND schemaname = 'public';
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SAMPLE OPTIMIZATION QUERIES TO RUN REGULARLY
-- ============================================================================

/*
-- Run these queries regularly for maintenance:

-- 1. Update table statistics (daily)
SELECT update_table_statistics();

-- 2. Clean up old data (weekly)
SELECT cleanup_old_data(90);

-- 3. Check optimization recommendations (weekly)
SELECT * FROM get_optimization_recommendations();

-- 4. Monitor database size (daily)
SELECT * FROM database_size_summary;

-- 5. Check active jobs (continuous monitoring)
SELECT * FROM active_jobs_summary;

-- 6. Monitor index usage (monthly)
SELECT * FROM index_usage_stats 
WHERE times_used = 0 
ORDER BY index_size DESC;
*/