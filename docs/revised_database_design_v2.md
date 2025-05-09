# Revised Database Design (v2)

## Core Tables with Monitoring Optimizations

```sql
-- Patients table remains unchanged
CREATE TABLE patients (
    patient_id VARCHAR(50) PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    date_of_birth DATE,
    gender CHAR(1),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Enhanced admissions table with monitoring fields
CREATE TABLE admissions (
    admission_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) REFERENCES patients(patient_id),
    admission_date TIMESTAMP,
    discharge_date TIMESTAMP,
    ward VARCHAR(100),
    bed_number VARCHAR(50),
    status VARCHAR(20),
    last_test_date TIMESTAMP,                    -- Added for monitoring
    hours_since_test INTEGER GENERATED ALWAYS AS 
        (EXTRACT(EPOCH FROM (NOW() - last_test_date))/3600) STORED,  -- Added for monitoring
    needs_attention BOOLEAN GENERATED ALWAYS AS 
        (status = 'Active' AND 
         (last_test_date IS NULL OR 
          EXTRACT(EPOCH FROM (NOW() - last_test_date))/3600 > 48)) STORED,  -- Added for monitoring
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Lab tests table with monitoring trigger
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
) PARTITION BY RANGE (test_date);

-- Monitoring queue for active tracking
CREATE TABLE monitoring_queue (
    patient_id VARCHAR(50) REFERENCES patients(patient_id),
    admission_id VARCHAR(50) REFERENCES admissions(admission_id),
    hours_since_test INTEGER,
    priority INTEGER GENERATED ALWAYS AS (
        CASE 
            WHEN hours_since_test >= 48 THEN 1
            WHEN hours_since_test >= 36 THEN 2
            ELSE 3
        END
    ) STORED,
    last_checked TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (patient_id, admission_id)
) PARTITION BY LIST (priority);
```

## Indexes for Monitoring

```sql
-- Admissions indexes
CREATE INDEX idx_admission_status_hours ON admissions(status, hours_since_test)
    WHERE status = 'Active';
CREATE INDEX idx_needs_attention ON admissions(needs_attention)
    WHERE needs_attention = true;
CREATE INDEX idx_admission_patient ON admissions(patient_id);

-- Lab tests indexes
CREATE INDEX idx_test_admission ON lab_tests(admission_id, test_date DESC);
CREATE INDEX idx_test_patient ON lab_tests(patient_id, test_date DESC);

-- Monitoring queue indexes
CREATE INDEX idx_monitoring_priority ON monitoring_queue(priority, hours_since_test DESC);
CREATE INDEX idx_monitoring_last_checked ON monitoring_queue(last_checked)
    WHERE priority = 1;
```

## Materialized Views

```sql
-- Main monitoring view
CREATE MATERIALIZED VIEW mv_patients_needing_tests AS
SELECT 
    p.patient_id,
    p.first_name,
    p.last_name,
    a.admission_id,
    a.ward,
    a.bed_number,
    a.admission_date,
    a.last_test_date,
    a.hours_since_test
FROM 
    patients p
    JOIN admissions a ON p.patient_id = a.patient_id
WHERE 
    a.needs_attention = true
WITH DATA;

CREATE UNIQUE INDEX idx_mv_monitoring_patient 
ON mv_patients_needing_tests(patient_id, admission_id);
```

## Triggers

```sql
-- Update last test date
CREATE OR REPLACE FUNCTION update_admission_last_test()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE admissions
    SET last_test_date = NEW.test_date
    WHERE admission_id = NEW.admission_id
    AND (last_test_date IS NULL OR NEW.test_date > last_test_date);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_last_test
AFTER INSERT OR UPDATE ON lab_tests
FOR EACH ROW
EXECUTE FUNCTION update_admission_last_test();

-- Maintain monitoring queue
CREATE OR REPLACE FUNCTION update_monitoring_queue()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.needs_attention THEN
        INSERT INTO monitoring_queue (patient_id, admission_id, hours_since_test)
        VALUES (NEW.patient_id, NEW.admission_id, NEW.hours_since_test)
        ON CONFLICT (patient_id, admission_id) 
        DO UPDATE SET 
            hours_since_test = NEW.hours_since_test;
    ELSE
        DELETE FROM monitoring_queue 
        WHERE patient_id = NEW.patient_id 
        AND admission_id = NEW.admission_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_monitoring_queue
AFTER INSERT OR UPDATE ON admissions
FOR EACH ROW
EXECUTE FUNCTION update_monitoring_queue();
```

## Functions

```sql
-- Get patients needing attention
CREATE OR REPLACE FUNCTION get_patients_needing_tests(
    p_ward VARCHAR DEFAULT NULL,
    p_min_hours INTEGER DEFAULT 48
)
RETURNS TABLE (
    patient_id VARCHAR,
    first_name VARCHAR,
    last_name VARCHAR,
    ward VARCHAR,
    bed_number VARCHAR,
    hours_since_test INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.patient_id,
        p.first_name,
        p.last_name,
        a.ward,
        a.bed_number,
        a.hours_since_test
    FROM 
        patients p
        JOIN admissions a ON p.patient_id = a.patient_id
    WHERE 
        a.needs_attention = true
        AND (p_ward IS NULL OR a.ward = p_ward)
        AND a.hours_since_test >= p_min_hours
    ORDER BY 
        a.hours_since_test DESC;
END;
$$ LANGUAGE plpgsql;

-- Process monitoring batch
CREATE OR REPLACE FUNCTION process_monitoring_batch(
    p_batch_size INTEGER DEFAULT 100
)
RETURNS TABLE (
    patient_id VARCHAR,
    hours_since_test INTEGER
) AS $$
BEGIN
    RETURN QUERY
    WITH batch AS (
        SELECT 
            mq.patient_id,
            mq.admission_id,
            mq.hours_since_test
        FROM 
            monitoring_queue mq
        WHERE 
            mq.priority = 1
        ORDER BY 
            mq.hours_since_test DESC
        LIMIT p_batch_size
        FOR UPDATE SKIP LOCKED
    )
    UPDATE monitoring_queue mq
    SET last_checked = NOW()
    FROM batch b
    WHERE mq.patient_id = b.patient_id
    AND mq.admission_id = b.admission_id
    RETURNING b.patient_id, b.hours_since_test;
END;
$$ LANGUAGE plpgsql;
```

## Performance Optimizations

1. **Partitioning**
   - Lab tests partitioned by date
   - Monitoring queue partitioned by priority
   - Enables efficient data management

2. **Generated Columns**
   - Pre-calculated hours since last test
   - Automatic priority calculation
   - Reduces query complexity

3. **Materialized Views**
   - Pre-computed monitoring data
   - Concurrent refresh support
   - Efficient read access

4. **Strategic Indexing**
   - Covers common query patterns
   - Supports monitoring operations
   - Optimizes join performance

This revised design optimizes for the 48-hour monitoring requirement while maintaining data integrity and system performance.