from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from db import get_db, init_db, SessionLocal
from models import Patient, LabTest, Admission, PatientOut
from datetime import datetime, timedelta
from typing import List
from load_data import load_all_data

app = FastAPI()

# Add CORS middleware for development purposes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    # Initialize database
    init_db()
    
    db = SessionLocal()
    try:
        # Load data into the database
        load_all_data(db)
    finally:
        db.close()

@app.get("/patients", response_model=List[PatientOut])
def get_patients(db: Session = Depends(get_db)):
    threshold = datetime.now() - timedelta(days=48)

    # latest lab test per unique patient
    subquery = (
        db.query(LabTest.patient_id, func.max(LabTest.order_time).label("last_test"))
        .group_by(LabTest.patient_id)
        .subquery()
    )
    # Patients admitted > 48 hours ago and no lab test or last test > 48 hours
    results = (
        db.query(
            Patient,
            Admission.admission_time,
            subquery.c.last_test,  # Use the aggregated last test time
            Admission.release_time
        )
        .join(Admission, Patient.id == Admission.patient_id)
        .outerjoin(subquery, Patient.id == subquery.c.patient_id)
        .filter(Admission.release_time == None)  # Patients must not be discharged
        .filter(Admission.admission_time < threshold)  # Patients must have been admitted more than 48 hours ago
        .filter((subquery.c.last_test == None) | (subquery.c.last_test < threshold))  # Either no lab test or the last test is older than 48 hours
        .distinct()  # Ensure each patient appears only once
        .all()
    )
    print(f"Found {len(results)} patients matching the criteria")

    return [
        PatientOut(
            id=patient.id,
            name=f"{patient.first_name} {patient.last_name}",
            admission_time=admission_time,
            last_test_time=last_test_time,
            discharge_time=release_time
        )
        for patient, admission_time, last_test_time, release_time in results
    ]
