"""create base tables

Revision ID: 001
Revises: 
Create Date: 2025-05-08 15:38:02.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create patients table
    op.create_table(
        'patients',
        sa.Column('patient_id', sa.String(50), primary_key=True),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('date_of_birth', sa.Date(), nullable=False),
        sa.Column('gender', sa.String(1), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.func.now(), onupdate=sa.func.now())
    )

    # Create admissions table with monitoring fields
    op.create_table(
        'admissions',
        sa.Column('admission_id', sa.String(50), primary_key=True),
        sa.Column('patient_id', sa.String(50), nullable=False),
        sa.Column('admission_date', sa.TIMESTAMP, nullable=False),
        sa.Column('discharge_date', sa.TIMESTAMP),
        sa.Column('ward', sa.String(100), nullable=False),
        sa.Column('bed_number', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('last_test_date', sa.TIMESTAMP),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.patient_id'], ondelete='CASCADE')
    )

    # Add generated column for hours since test
    op.execute("""
        ALTER TABLE admissions ADD COLUMN hours_since_test INTEGER 
        GENERATED ALWAYS AS (
            EXTRACT(EPOCH FROM (NOW() - last_test_date))/3600
        ) STORED;
    """)

    # Add generated column for needs_attention
    op.execute("""
        ALTER TABLE admissions ADD COLUMN needs_attention BOOLEAN 
        GENERATED ALWAYS AS (
            status = 'Active' AND 
            (last_test_date IS NULL OR 
             EXTRACT(EPOCH FROM (NOW() - last_test_date))/3600 > 48)
        ) STORED;
    """)

    # Create lab_tests table
    op.create_table(
        'lab_tests',
        sa.Column('test_id', sa.String(50), primary_key=True),
        sa.Column('patient_id', sa.String(50), nullable=False),
        sa.Column('admission_id', sa.String(50), nullable=False),
        sa.Column('test_type', sa.String(100), nullable=False),
        sa.Column('test_date', sa.TIMESTAMP, nullable=False),
        sa.Column('result', sa.Text),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('lab_location', sa.String(100), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.patient_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['admission_id'], ['admissions.admission_id'], ondelete='CASCADE')
    )

    # Create monitoring_queue table
    op.create_table(
        'monitoring_queue',
        sa.Column('patient_id', sa.String(50), nullable=False),
        sa.Column('admission_id', sa.String(50), nullable=False),
        sa.Column('hours_since_test', sa.Integer),
        sa.Column('last_checked', sa.TIMESTAMP, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.patient_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['admission_id'], ['admissions.admission_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('patient_id', 'admission_id')
    )

    # Add generated column for priority
    op.execute("""
        ALTER TABLE monitoring_queue ADD COLUMN priority INTEGER 
        GENERATED ALWAYS AS (
            CASE 
                WHEN hours_since_test >= 48 THEN 1
                WHEN hours_since_test >= 36 THEN 2
                ELSE 3
            END
        ) STORED;
    """)

    # Create indexes
    op.create_index('idx_admission_status_hours', 'admissions', 
                    ['status', 'hours_since_test'], 
                    postgresql_where=text("status = 'Active'"))
    op.create_index('idx_needs_attention', 'admissions', 
                    ['needs_attention'],
                    postgresql_where=text("needs_attention = true"))
    op.create_index('idx_admission_patient', 'admissions', ['patient_id'])
    op.create_index('idx_test_admission', 'lab_tests', ['admission_id', 'test_date'])
    op.create_index('idx_test_patient', 'lab_tests', ['patient_id', 'test_date'])
    op.create_index('idx_monitoring_priority', 'monitoring_queue', ['priority', 'hours_since_test'])

def downgrade():
    op.drop_table('monitoring_queue')
    op.drop_table('lab_tests')
    op.drop_table('admissions')
    op.drop_table('patients')