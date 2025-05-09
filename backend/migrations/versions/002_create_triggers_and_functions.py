"""create triggers and functions

Revision ID: 002
Revises: 001
Create Date: 2025-05-08 15:39:26.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade():
    # Create function to update last test date
    op.execute("""
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
    """)

    # Create trigger for updating last test date
    op.execute("""
        CREATE TRIGGER trg_update_last_test
        AFTER INSERT OR UPDATE ON lab_tests
        FOR EACH ROW
        EXECUTE FUNCTION update_admission_last_test();
    """)

    # Create function to update monitoring queue
    op.execute("""
        CREATE OR REPLACE FUNCTION update_monitoring_queue()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.needs_attention THEN
                INSERT INTO monitoring_queue (
                    patient_id, 
                    admission_id, 
                    hours_since_test
                )
                VALUES (
                    NEW.patient_id, 
                    NEW.admission_id, 
                    NEW.hours_since_test
                )
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
    """)

    # Create trigger for maintaining monitoring queue
    op.execute("""
        CREATE TRIGGER trg_monitoring_queue
        AFTER INSERT OR UPDATE ON admissions
        FOR EACH ROW
        EXECUTE FUNCTION update_monitoring_queue();
    """)

    # Create function to process monitoring batch
    op.execute("""
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
    """)

    # Create materialized view for patient monitoring
    op.execute("""
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
    """)

def downgrade():
    # Drop materialized view
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_patients_needing_tests;")
    
    # Drop triggers and functions
    op.execute("DROP TRIGGER IF EXISTS trg_monitoring_queue ON admissions;")
    op.execute("DROP FUNCTION IF EXISTS update_monitoring_queue;")
    op.execute("DROP TRIGGER IF EXISTS trg_update_last_test ON lab_tests;")
    op.execute("DROP FUNCTION IF EXISTS update_admission_last_test;")
    op.execute("DROP FUNCTION IF EXISTS process_monitoring_batch;")