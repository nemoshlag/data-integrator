import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from models import Base, Patient, Admission, LabTest, LabResult
from db import engine

def parse_datetime(date_str, time_str):
    if pd.isna(date_str):
        return None
    try:
        dt_str = f"{date_str} {time_str}" if not pd.isna(time_str) else date_str
        return pd.to_datetime(dt_str)
    except Exception:
        return None

def load_table_data(db: Session, df, model_class, transform_func):
    try:
        for _, row in df.iterrows():
            try:
                instance = transform_func(row)
                db.add(instance)
                db.flush()  # Check for constraints immediately
            except Exception as e:
                db.rollback()
                print(f"Error adding record: {str(e)}")
                continue
        db.commit()
        print(f"Successfully loaded {model_class.__name__} data")
    except Exception as e:
        db.rollback()
        print(f"Error loading {model_class.__name__} data: {str(e)}")
        raise e

def load_all_data(db: Session):
    try:
        # Drop and recreate all tables using SQLAlchemy metadata
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        
        # Transform functions for each model
        def transform_patient(row):
            return Patient(
                id=row.patient_id,
                first_name=row.first_name,
                last_name=row.last_name,
                date_of_birth=pd.to_datetime(row.date_of_birth),
                primary_physician=row.primary_physician,
                insurance_provider=row.insurance_provider,
                blood_type=row.blood_type,
                allergies=row.allergies
            )

        def transform_admission(row):
            return Admission(
                patient_id=row.patient_id,
                hospitalization_case_number=row.hospitalization_case_number,
                admission_time=parse_datetime(row.admission_date, row.admission_time),
                release_time=parse_datetime(row.release_date, row.release_time),
                department=row.department,
                room_number=row.room_number
            )

        def transform_lab_test(row):
            return LabTest(
                id=row.test_id,
                patient_id=row.patient_id,
                test_name=row.test_name,
                order_time=parse_datetime(row.order_date, row.order_time),
                ordering_physician=row.ordering_physician
            )

        def transform_lab_result(row):
            return LabResult(
                id=row.result_id,
                test_id=row.test_id,
                result_value=row.result_value,
                result_unit=row.result_unit,
                reference_range=row.reference_range,
                result_status=row.result_status,
                performed_time=parse_datetime(row.performed_date, row.performed_time),
                reviewing_physician=row.reviewing_physician
            )

        # Load data table by table with separate commits
        load_table_data(db, pd.read_csv("data/patient_information.csv"), Patient, transform_patient)
        load_table_data(db, pd.read_csv("data/admissions.csv"), Admission, transform_admission)
        load_table_data(db, pd.read_csv("data/lab_tests.csv"), LabTest, transform_lab_test)
        load_table_data(db, pd.read_csv("data/lab_results.csv"), LabResult, transform_lab_result)

        print("All data loaded successfully!")
    except Exception as e:
        print(f"Error in data loading process: {str(e)}")
        db.rollback()
        raise e
