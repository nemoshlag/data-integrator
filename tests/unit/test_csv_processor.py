"""Tests for CSV processing utilities."""
import pytest
import pandas as pd
from io import StringIO
from datetime import datetime

from src.utils.csv_processor import (
    process_csv_file,
    process_patient_file,
    process_admission_file,
    process_test_file,
    detect_file_type,
    validate_csv_format,
    CSVProcessingError
)

@pytest.fixture
def sample_patient_csv():
    """Sample patient CSV data."""
    return '''patient_id,first_name,last_name,date_of_birth,gender,email
P123456,John,Doe,1980-01-01,M,john.doe@example.com
P234567,Jane,Smith,1985-05-05,F,jane.smith@example.com'''

@pytest.fixture
def sample_admission_csv():
    """Sample admission CSV data."""
    return '''patient_id,admission_id,admission_date,ward,bed_number,status
P123456,A123456,2025-05-01T10:00:00,Cardiology,C101,Active
P234567,A234567,2025-05-02T11:00:00,Neurology,N202,Active'''

@pytest.fixture
def sample_test_csv():
    """Sample test CSV data."""
    return '''test_id,patient_id,admission_id,test_type,test_date,result,status,lab_location
T123456,P123456,A123456,Blood Test,2025-05-01T12:00:00,Normal,Completed,Main Lab
T234567,P234567,A234567,X-Ray,2025-05-02T13:00:00,Normal,Completed,Radiology'''

def test_process_patient_file(sample_patient_csv):
    """Test processing patient CSV file."""
    records, errors = process_patient_file(sample_patient_csv)
    
    assert len(errors) == 0
    assert len(records) == 2
    
    # Verify record fields
    record = records[0]
    assert record['patient_id'] == 'P123456'
    assert record['first_name'] == 'John'
    assert record['last_name'] == 'Doe'
    assert 'updated_at' in record

def test_process_admission_file(sample_admission_csv):
    """Test processing admission CSV file."""
    records, errors = process_admission_file(sample_admission_csv)
    
    assert len(errors) == 0
    assert len(records) == 2
    
    # Verify record fields
    record = records[0]
    assert record['admission_id'] == 'A123456'
    assert record['ward'] == 'Cardiology'
    assert record['status'] == 'Active'

def test_process_test_file(sample_test_csv):
    """Test processing test CSV file."""
    records, errors = process_test_file(sample_test_csv)
    
    assert len(errors) == 0
    assert len(records) == 2
    
    # Verify record fields
    record = records[0]
    assert record['test_id'] == 'T123456'
    assert record['test_type'] == 'Blood Test'
    assert record['status'] == 'Completed'

def test_detect_file_type():
    """Test file type detection."""
    # Test patient file
    df = pd.DataFrame({
        'patient_id': [],
        'first_name': [],
        'last_name': [],
        'date_of_birth': [],
        'gender': []
    })
    assert detect_file_type(df) == 'patients'
    
    # Test admission file
    df = pd.DataFrame({
        'admission_id': [],
        'ward': [],
        'bed_number': []
    })
    assert detect_file_type(df) == 'admissions'
    
    # Test test file
    df = pd.DataFrame({
        'test_id': [],
        'test_type': [],
        'test_date': []
    })
    assert detect_file_type(df) == 'tests'
    
    # Test invalid file
    df = pd.DataFrame({'invalid': []})
    with pytest.raises(ValueError):
        detect_file_type(df)

def test_validate_csv_format():
    """Test CSV format validation."""
    # Test valid patient format
    df = pd.DataFrame({
        'patient_id': [],
        'first_name': [],
        'last_name': [],
        'date_of_birth': [],
        'gender': []
    })
    errors = validate_csv_format(df, 'patients')
    assert len(errors) == 0
    
    # Test missing columns
    df = pd.DataFrame({'invalid': []})
    errors = validate_csv_format(df, 'patients')
    assert len(errors) == 1
    assert 'missing_columns' in errors[0]['error']

def test_process_invalid_data():
    """Test processing invalid data."""
    # Test invalid patient data
    invalid_patient_csv = '''patient_id,first_name,last_name,date_of_birth,gender
invalid_id,John,Doe,invalid_date,X'''
    
    records, errors = process_patient_file(invalid_patient_csv)
    assert len(errors) == 1
    assert len(records) == 0
    
    # Test invalid admission data
    invalid_admission_csv = '''patient_id,admission_id,admission_date,ward,bed_number,status
P123456,invalid_id,invalid_date,Ward,123,Invalid'''
    
    records, errors = process_admission_file(invalid_admission_csv)
    assert len(errors) == 1
    assert len(records) == 0

def test_process_mixed_valid_invalid():
    """Test processing mix of valid and invalid records."""
    mixed_csv = '''patient_id,first_name,last_name,date_of_birth,gender
P123456,John,Doe,1980-01-01,M
invalid_id,Jane,Smith,invalid_date,X'''
    
    records, errors = process_patient_file(mixed_csv)
    assert len(records) == 1
    assert len(errors) == 1
    assert records[0]['patient_id'] == 'P123456'

def test_process_empty_file():
    """Test processing empty file."""
    empty_csv = 'patient_id,first_name,last_name,date_of_birth,gender\n'
    
    records, errors = process_patient_file(empty_csv)
    assert len(records) == 0
    assert len(errors) == 0

def test_process_csv_file_integration(sample_patient_csv, sample_admission_csv, sample_test_csv):
    """Test integrated CSV processing."""
    # Test patient file
    records, errors = process_csv_file(sample_patient_csv)
    assert len(records) == 2
    assert len(errors) == 0
    
    # Test admission file
    records, errors = process_csv_file(sample_admission_csv)
    assert len(records) == 2
    assert len(errors) == 0
    
    # Test test file
    records, errors = process_csv_file(sample_test_csv)
    assert len(records) == 2
    assert len(errors) == 0

def test_error_handling():
    """Test error handling."""
    # Test invalid CSV format
    invalid_csv = 'invalid,csv\ndata'
    with pytest.raises(Exception):
        process_csv_file(invalid_csv)
    
    # Test invalid file type
    invalid_type_csv = 'column1,column2\nvalue1,value2'
    with pytest.raises(ValueError):
        process_csv_file(invalid_type_csv)