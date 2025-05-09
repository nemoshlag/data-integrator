"""CSV processing utilities for data ingestion."""
import pandas as pd
from typing import Dict, List, Any, Tuple
from datetime import datetime
import io

from .logging import get_logger
from .validation import (
    validate_patient_record,
    validate_admission_record,
    validate_test_record,
    sanitize_record
)
from .models import Patient, Admission, Test

logger = get_logger('csv_processor')

class CSVProcessingError(Exception):
    """Custom exception for CSV processing errors."""
    def __init__(self, message: str, details: Dict[str, Any]):
        super().__init__(message)
        self.details = details

def validate_csv_format(df: pd.DataFrame, file_type: str) -> List[Dict[str, Any]]:
    """Validate CSV format and required columns."""
    required_columns = {
        'patients': [
            'patient_id', 'first_name', 'last_name',
            'date_of_birth', 'gender'
        ],
        'admissions': [
            'patient_id', 'admission_id', 'admission_date',
            'ward', 'bed_number', 'status'
        ],
        'tests': [
            'test_id', 'patient_id', 'admission_id', 'test_type',
            'test_date', 'result', 'status', 'lab_location'
        ]
    }

    errors = []
    
    # Check if file type is valid
    if file_type not in required_columns:
        raise ValueError(f"Invalid file type: {file_type}")
    
    # Check for required columns
    missing_columns = set(required_columns[file_type]) - set(df.columns)
    if missing_columns:
        errors.append({
            'error': 'missing_columns',
            'columns': list(missing_columns)
        })
    
    return errors

def process_patient_file(content: str) -> Tuple[List[Dict], List[Dict]]:
    """Process patient CSV file."""
    try:
        # Read CSV content
        df = pd.read_csv(io.StringIO(content))
        
        # Validate format
        format_errors = validate_csv_format(df, 'patients')
        if format_errors:
            raise CSVProcessingError("Invalid CSV format", {'errors': format_errors})

        # Process records
        records = []
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Convert row to dict and sanitize
                record = sanitize_record(row.to_dict())
                
                # Validate record
                validation_errors = validate_patient_record(record)
                if validation_errors:
                    errors.append({
                        'row': index + 2,  # +2 for header row and 0-based index
                        'errors': validation_errors
                    })
                    continue
                
                # Create patient model
                patient = Patient(
                    patient_id=record['patient_id'],
                    first_name=record['first_name'],
                    last_name=record['last_name'],
                    date_of_birth=record['date_of_birth'],
                    gender=record['gender'],
                    email=record.get('email'),
                    updated_at=datetime.now().isoformat()
                )
                
                records.append(patient.to_dict())
                
            except Exception as e:
                errors.append({
                    'row': index + 2,
                    'errors': [str(e)]
                })
        
        return records, errors
        
    except Exception as e:
        logger.error(f"Error processing patient file: {str(e)}")
        raise

def process_admission_file(content: str) -> Tuple[List[Dict], List[Dict]]:
    """Process admission CSV file."""
    try:
        # Read CSV content
        df = pd.read_csv(io.StringIO(content))
        
        # Validate format
        format_errors = validate_csv_format(df, 'admissions')
        if format_errors:
            raise CSVProcessingError("Invalid CSV format", {'errors': format_errors})

        # Process records
        records = []
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Convert row to dict and sanitize
                record = sanitize_record(row.to_dict())
                
                # Validate record
                validation_errors = validate_admission_record(record)
                if validation_errors:
                    errors.append({
                        'row': index + 2,
                        'errors': validation_errors
                    })
                    continue
                
                # Create admission model
                admission = Admission(
                    patient_id=record['patient_id'],
                    admission_id=record['admission_id'],
                    admission_date=record['admission_date'],
                    ward=record['ward'],
                    bed_number=record['bed_number'],
                    status=record['status'],
                    updated_at=datetime.now().isoformat()
                )
                
                records.append(admission.to_dict())
                
            except Exception as e:
                errors.append({
                    'row': index + 2,
                    'errors': [str(e)]
                })
        
        return records, errors
        
    except Exception as e:
        logger.error(f"Error processing admission file: {str(e)}")
        raise

def process_test_file(content: str) -> Tuple[List[Dict], List[Dict]]:
    """Process test CSV file."""
    try:
        # Read CSV content
        df = pd.read_csv(io.StringIO(content))
        
        # Validate format
        format_errors = validate_csv_format(df, 'tests')
        if format_errors:
            raise CSVProcessingError("Invalid CSV format", {'errors': format_errors})

        # Process records
        records = []
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Convert row to dict and sanitize
                record = sanitize_record(row.to_dict())
                
                # Validate record
                validation_errors = validate_test_record(record)
                if validation_errors:
                    errors.append({
                        'row': index + 2,
                        'errors': validation_errors
                    })
                    continue
                
                # Create test model
                test = Test(
                    test_id=record['test_id'],
                    patient_id=record['patient_id'],
                    admission_id=record['admission_id'],
                    test_type=record['test_type'],
                    test_date=record['test_date'],
                    result=record['result'],
                    status=record['status'],
                    lab_location=record['lab_location'],
                    updated_at=datetime.now().isoformat()
                )
                
                records.append(test.to_dict())
                
            except Exception as e:
                errors.append({
                    'row': index + 2,
                    'errors': [str(e)]
                })
        
        return records, errors
        
    except Exception as e:
        logger.error(f"Error processing test file: {str(e)}")
        raise

def detect_file_type(df: pd.DataFrame) -> str:
    """Detect the type of CSV file based on its columns."""
    columns = set(df.columns)
    
    if {'test_id', 'test_type', 'test_date'}.issubset(columns):
        return 'tests'
    elif {'admission_id', 'ward', 'bed_number'}.issubset(columns):
        return 'admissions'
    elif {'first_name', 'last_name', 'date_of_birth'}.issubset(columns):
        return 'patients'
    else:
        raise ValueError("Unable to determine file type from columns")

def process_csv_file(content: str) -> Tuple[List[Dict], List[Dict]]:
    """Process a CSV file and return processed records and errors."""
    try:
        # Read CSV content
        df = pd.read_csv(io.StringIO(content))
        
        # Detect file type
        file_type = detect_file_type(df)
        
        # Process based on file type
        if file_type == 'patients':
            return process_patient_file(content)
        elif file_type == 'admissions':
            return process_admission_file(content)
        elif file_type == 'tests':
            return process_test_file(content)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
            
    except Exception as e:
        logger.error(f"Error processing CSV file: {str(e)}")
        raise