# Revised Database Design

After analyzing the sample data structure, we recommend using **PostgreSQL** as the primary database instead of the previously suggested hybrid approach. Here's why:

## Rationale

1. **Data Structure**
   - The data is highly relational with clear parent-child relationships
   - Strong referential integrity is important for medical data
   - The schema is well-defined and stable
   - JOINs will be frequently needed for monitoring

2. **Query Patterns**
   - Need to find patients without tests for >48 hours requires complex queries
   - Time-based analysis is better suited for PostgreSQL's datetime functions
   - Window functions useful for analyzing test patterns over time

3. **Data Consistency**
   - ACID compliance crucial for medical data
   - Transaction support needed for related updates
   - Referential integrity maintains data quality

## Database Schema

```sql
-- Patients table
CREATE TABLE patients (
    patient_id VARCHAR(50) PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    date_of_birth DATE,
    gender CHAR(1),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Admissions table
CREATE TABLE admissions (
    admission_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) REFERENCES patients(patient_id),
    admission_date TIMESTAMP,
    discharge_date TIMESTAMP,
    ward VARCHAR(100),
    bed_number VARCHAR(50),
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Laboratory tests table
CREATE TABLE lab_tests (
    test_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) REFERENCES patients(patient_id),
    admission_id VARCHAR(50) REFERENCES admissions(admission_id),
    test_type VARCHAR(100),
    test_date TIMESTAMP,
    result TEXT,
    status VARCHAR(20),
    lab_location VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_admission_patient ON admissions(patient_id);
CREATE INDEX idx_test_admission ON lab_tests(admission_id);
CREATE INDEX idx_test_patient_date ON lab_tests(patient_id, test_date);
CREATE INDEX idx_admission_status ON admissions(status);
```

## Performance Optimizations

1. **Partitioning Strategy**
   ```sql
   -- Partition lab_tests by month
   CREATE TABLE lab_tests (
       ...
   ) PARTITION BY RANGE (test_date);
   
   -- Create monthly partitions
   CREATE TABLE lab_tests_y2023m05 PARTITION OF lab_tests
   FOR VALUES FROM ('2023-05-01') TO ('2023-06-01');
   ```

2. **Materialized Views**
   ```sql
   -- View for patients without recent tests
   CREATE MATERIALIZED VIEW mv_patients_without_tests AS
   SELECT 
       p.patient_id,
       p.first_name,
       p.last_name,
       a.admission_id,
       a.ward,
       a.admission_date,
       MAX(lt.test_date) as last_test_date,
       NOW() - MAX(lt.test_date) as time_since_last_test
   FROM patients p
   JOIN admissions a ON p.patient_id = a.patient_id
   LEFT JOIN lab_tests lt ON a.admission_id = lt.admission_id
   WHERE a.status = 'Active'
   GROUP BY p.patient_id, p.first_name, p.last_name, a.admission_id, a.ward, a.admission_date
   HAVING NOW() - MAX(lt.test_date) > INTERVAL '48 hours'
   OR MAX(lt.test_date) IS NULL;
   ```

## Scaling Strategy

1. **Connection Pooling**
   - Use PgBouncer for connection pooling
   - Configure pool size based on Lambda concurrency limits

2. **Read Replicas**
   - Deploy read replicas for report generation
   - Use replicas for the materialized view refreshes

3. **Caching Layer**
   - Implement Redis caching for frequently accessed data
   - Cache materialized view results
   - Cache patient status information

## Lambda Integration

```python
# Example Lambda function for querying patients without recent tests
def get_patients_without_tests(event, context):
    with pg_pool.getconn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM mv_patients_without_tests
                WHERE time_since_last_test > interval '48 hours'
                ORDER BY time_since_last_test DESC;
            """)
            return {
                'statusCode': 200,
                'body': json.dumps(cur.fetchall())
            }
```

## Data Update Strategy

1. **Real-time Updates**
   ```python
   def process_update(event, context):
       with pg_pool.getconn() as conn:
           with conn.cursor() as cur:
               # Begin transaction
               cur.execute("BEGIN")
               try:
                   # Update tables
                   update_tables(cur, event['data'])
                   # Refresh materialized view
                   cur.execute("""
                       REFRESH MATERIALIZED VIEW CONCURRENTLY mv_patients_without_tests
                   """)
                   # Commit transaction
                   cur.execute("COMMIT")
               except Exception as e:
                   cur.execute("ROLLBACK")
                   raise e
   ```

2. **Batch Updates**
   - Schedule materialized view refreshes
   - Archive old data to cold storage
   - Clean up expired sessions

## Monitoring and Alerts

1. **Performance Monitoring**
   - Track query performance
   - Monitor connection pool usage
   - Watch for long-running transactions

2. **Data Quality**
   - Validate data consistency
   - Check for orphaned records
   - Monitor update frequencies

3. **Business Alerts**
   - Alert on patients without tests > 48 hours
   - Monitor admission patterns
   - Track test result trends

This design provides a robust, scalable solution that maintains data integrity while delivering the performance needed for real-time monitoring of patient test status.