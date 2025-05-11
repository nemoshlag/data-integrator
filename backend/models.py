from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from datetime import datetime

Base = declarative_base()

class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    date_of_birth = Column(DateTime)
    primary_physician = Column(String)
    insurance_provider = Column(String)
    blood_type = Column(String)
    allergies = Column(String)

class Admission(Base):
    __tablename__ = "admissions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer)
    hospitalization_case_number = Column(Integer)
    admission_time = Column(DateTime)
    release_time = Column(DateTime, nullable=True)
    department = Column(String)
    room_number = Column(String)

class LabTest(Base):
    __tablename__ = "lab_tests"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer)
    test_name = Column(String)
    order_time = Column(DateTime)
    ordering_physician = Column(String)

class LabResult(Base):
    __tablename__ = "lab_results"
    id = Column(Integer, primary_key=True)
    test_id = Column(Integer)
    result_value = Column(Float)
    result_unit = Column(String)
    reference_range = Column(String)
    result_status = Column(String)
    performed_time = Column(DateTime)
    reviewing_physician = Column(String)

class PatientOut(BaseModel):
    id: int
    name: str
    admission_time: datetime
    last_test_time: datetime | None
    discharge_time: datetime | None

    class Config:
        orm_mode = True
        