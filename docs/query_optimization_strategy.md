# PostgreSQL Query Optimization Strategy

## 1. Index Strategy

### 1.1 Primary Indexes
```sql
-- Patient search optimization
CREATE INDEX idx_patients_name ON patients (last_name, first_name);
CREATE INDEX idx_patients_dob ON patients (date_of_birth);

-- Admission monitoring
CREATE INDEX idx_admissions_status_date ON admissions (status, last_test_date);
CREATE INDEX idx_admissions_ward ON admissions (ward, status);

-- Test result queries
CREATE INDEX idx_tests_date_type ON tests (test_date, test_type);
CREATE INDEX idx_tests_status ON tests (status, test_date);

-- Composite indexes for common joins
CREATE INDEX idx_admission_patient ON admissions (patient_id, admission_date);
CREATE INDEX idx_test_admission ON tests (admission_id, test_date);
```

### 1.2 Partial Indexes
```sql
-- Active admissions only
CREATE INDEX idx_active_admissions ON admissions (last_test_date)
WHERE status = 'Active';

-- Recent tests
CREATE INDEX idx_recent_tests ON tests (test_date, result)
WHERE test_date > CURRENT_DATE - INTERVAL '7 days';

-- Priority patients
CREATE INDEX idx_priority_patients ON admissions (last_test_date)
WHERE ward IN ('ICU', 'Emergency', 'CCU') AND status = 'Active';
```

## 2. Materialized Views

### 2.1 Patient Monitoring View
```sql
CREATE MATERIALIZED VIEW patient_monitoring_summary AS
SELECT 
    p.patient_id,
    p.first_name,
    p.last_name,
    a.admission_id,
    a.ward,
    a.bed_number,
    a.status,
    a.last_test_date,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - a.last_test_date))/3600 as hours_since_test,
    COUNT(t.test_id) as total_tests,
    MAX(t.test_date) as latest_test_date
FROM patients p
JOIN admissions a ON p.patient_id = a.patient_id
LEFT JOIN tests t ON a.admission_id = t.admission_id
WHERE a.status = 'Active'
GROUP BY p.patient_id, p.first_name, p.last_name, a.admission_id, a.ward, 
         a.bed_number, a.status, a.last_test_date;

-- Create index on materialized view
CREATE INDEX idx_monitoring_hours ON patient_monitoring_summary (hours_since_test);
CREATE INDEX idx_monitoring_ward ON patient_monitoring_summary (ward);

-- Refresh strategy
CREATE OR REPLACE FUNCTION refresh_monitoring_summary()
RETURNS trigger AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY patient_monitoring_summary;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER refresh_monitoring_summary_trigger
AFTER INSERT OR UPDATE OR DELETE ON tests
FOR EACH STATEMENT
EXECUTE FUNCTION refresh_monitoring_summary();
```

## 3. Query Optimization

### 3.1 Common Query Patterns
```sql
-- Patient search optimization
PREPARE find_patient(text) AS
SELECT patient_id, first_name, last_name, date_of_birth
FROM patients
WHERE last_name ILIKE $1 || '%'
ORDER BY last_name, first_name
LIMIT 20;

-- Active admission status
PREPARE get_admission_status(text) AS
SELECT a.*, p.first_name, p.last_name,
       EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - a.last_test_date))/3600 as hours_since_test
FROM admissions a
JOIN patients p ON a.patient_id = p.patient_id
WHERE a.status = 'Active'
  AND a.patient_id = $1;

-- Recent test results
PREPARE get_recent_tests(text, interval) AS
SELECT t.*, p.first_name, p.last_name
FROM tests t
JOIN admissions a ON t.admission_id = a.admission_id
JOIN patients p ON a.patient_id = p.patient_id
WHERE t.test_date > CURRENT_TIMESTAMP - $2
  AND a.patient_id = $1
ORDER BY t.test_date DESC;
```

### 3.2 Optimization Functions
```sql
-- Analyze query performance
CREATE OR REPLACE FUNCTION analyze_query_performance(
    p_query text,
    p_params text[] DEFAULT NULL
) RETURNS TABLE (
    execution_time numeric,
    plan_time numeric,
    total_cost numeric,
    actual_rows bigint,
    actual_time numeric,
    query_plan json
) AS $$
BEGIN
    RETURN QUERY
    EXECUTE 'EXPLAIN (ANALYZE, FORMAT JSON) ' || p_query
    USING p_params;
END;
$$ LANGUAGE plpgsql;

-- Index usage analysis
CREATE OR REPLACE VIEW index_usage_analysis AS
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as number_of_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched,
    idx_scan::float / NULLIF(seq_scan, 0) as index_to_seq_scan_ratio
FROM pg_stat_user_indexes
JOIN pg_stat_user_tables 
    ON pg_stat_user_indexes.schemaname = pg_stat_user_tables.schemaname
    AND pg_stat_user_indexes.tablename = pg_stat_user_tables.relname
WHERE idx_scan > 0
ORDER BY idx_scan DESC;
```

## 4. Performance Monitoring

### 4.1 Slow Query Detection
```sql
CREATE VIEW slow_queries AS
WITH query_stats AS (
    SELECT 
        query,
        total_time / calls as avg_time,
        calls,
        rows,
        shared_blks_hit + shared_blks_read as total_blocks
    FROM pg_stat_statements
    WHERE total_time / calls > 100  -- milliseconds
)
SELECT 
    query,
    avg_time,
    calls,
    rows,
    total_blocks,
    total_blocks::float / NULLIF(rows, 0) as blocks_per_row
FROM query_stats
ORDER BY avg_time DESC;
```

### 4.2 Performance Metrics Collection
```python
class QueryPerformanceMonitor:
    def __init__(self):
        self.metrics = []
    
    async def collect_metrics(self):
        """Collect query performance metrics."""
        metrics = await self.execute_query("""
            SELECT 
                queryid,
                query,
                calls,
                total_time / calls as avg_time,
                rows / calls as avg_rows,
                shared_blks_hit / calls as avg_cache_hits,
                shared_blks_read / calls as avg_disk_reads,
                temp_blks_written / calls as avg_temp_writes
            FROM pg_stat_statements
            WHERE calls > 100
            ORDER BY total_time DESC
            LIMIT 100
        """)
        
        return self.analyze_metrics(metrics)
    
    def analyze_metrics(self, metrics):
        """Analyze collected metrics."""
        return {
            'slow_queries': self._identify_slow_queries(metrics),
            'cache_misses': self._identify_cache_misses(metrics),
            'high_disk_reads': self._identify_disk_reads(metrics),
            'recommendations': self._generate_recommendations(metrics)
        }
```

## 5. Query Optimization Guidelines

### 5.1 General Guidelines
```yaml
optimization_rules:
  - rule: "Use EXPLAIN ANALYZE for query analysis"
    importance: High
    
  - rule: "Create indexes for frequently filtered columns"
    importance: High
    
  - rule: "Use materialized views for complex aggregations"
    importance: Medium
    
  - rule: "Implement connection pooling"
    importance: High
    
  - rule: "Regular VACUUM ANALYZE"
    importance: High
```

### 5.2 Specific Optimizations
```sql
-- Use CTEs for complex queries
WITH active_patients AS (
    SELECT patient_id, admission_id
    FROM admissions
    WHERE status = 'Active'
),
recent_tests AS (
    SELECT admission_id, COUNT(*) as test_count
    FROM tests
    WHERE test_date > CURRENT_DATE - INTERVAL '24 hours'
    GROUP BY admission_id
)
SELECT p.*, rt.test_count
FROM active_patients ap
JOIN patients p ON ap.patient_id = p.patient_id
LEFT JOIN recent_tests rt ON ap.admission_id = rt.admission_id;

-- Use LATERAL joins for better performance
SELECT p.*, t.*
FROM patients p
CROSS JOIN LATERAL (
    SELECT *
    FROM tests
    WHERE patient_id = p.patient_id
    ORDER BY test_date DESC
    LIMIT 5
) t;
```

This strategy ensures optimal query performance while maintaining data integrity and system responsiveness. Regular monitoring and adjustment of these optimizations is crucial for maintaining performance as the system grows.