# Query Optimization for Hospital Monitoring System

## Key Query Patterns

### 1. Finding Patients Without Recent Tests
```sql
-- Using multiple tables allows efficient indexing and joining
CREATE INDEX idx_test_date ON lab_tests(test_date);
CREATE INDEX idx_admission_status ON admissions(status);

-- Efficient query using indexes
SELECT 
    p.patient_id,
    p.first_name,
    p.last_name,
    a.admission_date,
    MAX(t.test_date) as last_test_date,
    NOW() - MAX(t.test_date) as time_since_last_test
FROM 
    patients p
    JOIN admissions a ON p.patient_id = a.patient_id
    LEFT JOIN lab_tests t ON a.admission_id = t.admission_id
WHERE 
    a.status = 'Active'
GROUP BY 
    p.patient_id, p.first_name, p.last_name, a.admission_date
HAVING 
    MAX(t.test_date) < NOW() - INTERVAL '48 hours'
    OR MAX(t.test_date) IS NULL;
```

### 2. Patient History View
```sql
-- Efficient retrieval of patient history
CREATE INDEX idx_patient_admission ON admissions(patient_id, admission_date);
CREATE INDEX idx_admission_tests ON lab_tests(admission_id, test_date);

-- Query for complete patient history
SELECT 
    a.admission_date,
    a.ward,
    t.test_type,
    t.test_date,
    t.result
FROM 
    admissions a
    LEFT JOIN lab_tests t ON a.admission_id = t.admission_id
WHERE 
    a.patient_id = :patient_id
ORDER BY 
    a.admission_date DESC, t.test_date DESC;
```

## Performance Optimizations

### 1. Materialized Views
```sql
-- Materialized view for patients without recent tests
CREATE MATERIALIZED VIEW mv_patients_without_tests AS
SELECT 
    p.patient_id,
    p.first_name,
    p.last_name,
    a.admission_id,
    a.ward,
    MAX(t.test_date) as last_test_date
FROM 
    patients p
    JOIN admissions a ON p.patient_id = a.patient_id
    LEFT JOIN lab_tests t ON a.admission_id = t.admission_id
WHERE 
    a.status = 'Active'
GROUP BY 
    p.patient_id, p.first_name, p.last_name, a.admission_id, a.ward;

-- Refresh strategy
CREATE OR REPLACE FUNCTION refresh_mv_patients_without_tests()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_patients_without_tests;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_refresh_mv_patients
AFTER INSERT OR UPDATE OR DELETE ON lab_tests
FOR EACH STATEMENT
EXECUTE FUNCTION refresh_mv_patients_without_tests();
```

### 2. Partitioning Strategy
```sql
-- Partition lab_tests by month for efficient historical queries
CREATE TABLE lab_tests (
    test_id VARCHAR(50),
    patient_id VARCHAR(50),
    admission_id VARCHAR(50),
    test_type VARCHAR(100),
    test_date TIMESTAMP,
    result TEXT,
    status VARCHAR(20)
) PARTITION BY RANGE (test_date);

-- Create monthly partitions
CREATE TABLE lab_tests_y2023m05 PARTITION OF lab_tests
    FOR VALUES FROM ('2023-05-01') TO ('2023-06-01');

-- Automatically create new partitions
CREATE OR REPLACE PROCEDURE create_next_month_partition()
LANGUAGE plpgsql
AS $$
DECLARE
    next_month date;
    partition_name text;
    partition_sql text;
BEGIN
    next_month := date_trunc('month', now()) + interval '1 month';
    partition_name := 'lab_tests_y' || 
                     to_char(next_month, 'YYYY') ||
                     'm' || 
                     to_char(next_month, 'MM');
    
    partition_sql := format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF lab_tests
         FOR VALUES FROM (%L) TO (%L)',
        partition_name,
        next_month,
        next_month + interval '1 month'
    );
    
    EXECUTE partition_sql;
END;
$$;
```

## Caching Strategy

### 1. Redis Caching
```python
# Cache frequently accessed data
def get_patient_status(patient_id: str) -> Dict:
    cache_key = f"patient_status:{patient_id}"
    
    # Try to get from cache
    cached_data = redis_client.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
        
    # If not in cache, query database
    with get_db() as db:
        status = db.query(
            Patient, Admission, func.max(LabTest.test_date)
        ).join(Admission).outerjoin(LabTest)\
         .filter(Patient.patient_id == patient_id)\
         .first()
        
        # Cache for 5 minutes
        redis_client.setex(
            cache_key,
            300,
            json.dumps(status)
        )
        
        return status
```

### 2. Invalidation Strategy
```python
def invalidate_patient_cache(patient_id: str) -> None:
    """Invalidate patient cache on data updates."""
    cache_key = f"patient_status:{patient_id}"
    redis_client.delete(cache_key)
    
    # Also invalidate related lists
    redis_client.delete("patients_without_tests")
```

## Benefits of Multi-Table Design for Queries

1. **Efficient Indexing**
   - Can create targeted indexes for each table
   - Smaller index sizes due to fewer columns
   - Better query optimizer statistics

2. **Parallel Query Execution**
   - Database can parallelize operations across tables
   - More efficient use of CPU cores
   - Better overall performance

3. **Memory Usage**
   - Smaller working sets in memory
   - More efficient query execution plans
   - Better buffer cache utilization

4. **Maintenance Operations**
   - Can rebuild indexes on smaller tables
   - Easier to manage table statistics
   - More efficient VACUUM operations

This optimization strategy ensures our hospital monitoring system can efficiently handle:
- Real-time patient monitoring
- Historical data analysis
- Complex reporting requirements
- High-volume data ingestion