"""Validation utilities for data processing and API requests."""
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, validator, Field
import re
import pandas as pd

from .logging import get_logger

logger = get_logger('validation')

# Regular expressions for validation
PATIENT_ID_REGEX = r'^P\d{6}$'
ADMISSION_ID_REGEX = r'^A\d{6}$'
TEST_ID_REGEX = r'^T\d{6}$'
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

class PatientData(BaseModel):
    """Patient data validation model."""
    patient_id: str = Field(..., regex=PATIENT_ID_REGEX)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    date_of_birth: str
    gender: str = Field(..., regex='^[MF]$')
    email: Optional[str] = Field(None, regex=EMAIL_REGEX)

    @validator('date_of_birth')
    def validate_date_of_birth(cls, v):
        """Validate date of birth format and range."""
        try:
            date = datetime.strptime(v, '%Y-%m-%d')
            if date > datetime.now():
                raise ValueError("Date of birth cannot be in the future")
            return v
        except ValueError as e:
            raise ValueError(f"Invalid date format: {str(e)}")

class AdmissionData(BaseModel):
    """Admission data validation model."""
    admission_id: str = Field(..., regex=ADMISSION_ID_REGEX)
    patient_id: str = Field(..., regex=PATIENT_ID_REGEX)
    admission_date: str
    ward: str = Field(..., min_length=1, max_length=50)
    bed_number: str = Field(..., min_length=1, max_length=10)
    status: str = Field(..., regex='^(Active|Discharged)$')

    @validator('admission_date')
    def validate_admission_date(cls, v):
        """Validate admission date format."""
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError("Invalid ISO format date")

class TestData(BaseModel):
    """Test data validation model."""
    test_id: str = Field(..., regex=TEST_ID_REGEX)
    patient_id: str = Field(..., regex=PATIENT_ID_REGEX)
    admission_id: str = Field(..., regex=ADMISSION_ID_REGEX)
    test_type: str = Field(..., min_length=1, max_length=50)
    test_date: str
    result: str
    status: str = Field(..., regex='^(Ordered|InProgress|Completed)$')
    lab_location: str = Field(..., min_length=1, max_length=50)

    @validator('test_date')
    def validate_test_date(cls, v):
        """Validate test date format."""
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError("Invalid ISO format date")

def validate_csv_data(df: pd.DataFrame, expected_columns: List[str]) -> List[Dict[str, Any]]:
    """Validate CSV data against expected columns and format."""
    errors = []
    
    # Check for required columns
    missing_columns = set(expected_columns) - set(df.columns)
    if missing_columns:
        errors.append({
            'type': 'missing_columns',
            'details': f"Missing required columns: {', '.join(missing_columns)}"
        })
        return errors

    # Convert empty strings to None
    df = df.replace(r'^\s*$', None, regex=True)

    # Check for null values in required fields
    for col in expected_columns:
        null_rows = df[df[col].isnull()].index.tolist()
        if null_rows:
            errors.append({
                'type': 'null_values',
                'column': col,
                'rows': null_rows
            })

    return errors

def validate_patient_record(record: Dict[str, Any]) -> List[str]:
    """Validate a patient record."""
    try:
        PatientData(**record)
        return []
    except Exception as e:
        return [str(e)]

def validate_admission_record(record: Dict[str, Any]) -> List[str]:
    """Validate an admission record."""
    try:
        AdmissionData(**record)
        return []
    except Exception as e:
        return [str(e)]

def validate_test_record(record: Dict[str, Any]) -> List[str]:
    """Validate a test record."""
    try:
        TestData(**record)
        return []
    except Exception as e:
        return [str(e)]

def validate_request_params(
    params: Dict[str, Any],
    required: List[str],
    optional: Optional[Dict[str, Any]] = None
) -> Tuple[bool, List[str]]:
    """Validate request parameters."""
    errors = []
    
    # Check required parameters
    for param in required:
        if param not in params:
            errors.append(f"Missing required parameter: {param}")
        elif not params[param]:
            errors.append(f"Empty value for required parameter: {param}")
    
    # Validate optional parameters if provided
    if optional:
        for param, validator_func in optional.items():
            if param in params and params[param]:
                try:
                    validator_func(params[param])
                except ValueError as e:
                    errors.append(f"Invalid value for {param}: {str(e)}")
    
    return len(errors) == 0, errors

def sanitize_string(value: str) -> str:
    """Sanitize string input."""
    if not value:
        return value
    # Remove control characters and non-printable characters
    return re.sub(r'[\x00-\x1F\x7F-\x9F]', '', str(value))

def sanitize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize all string values in a record."""
    return {
        key: sanitize_string(value) if isinstance(value, str) else value
        for key, value in record.items()
    }