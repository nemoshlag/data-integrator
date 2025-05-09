"""Tests for validation utilities."""
import pytest
import pandas as pd
from datetime import datetime
from pydantic import ValidationError

from src.utils.validation import (
    PatientData,
    AdmissionData,
    TestData,
    validate_csv_data,
    validate_patient_record,
    validate_admission_record,
    validate_test_record,
    validate_request_params,
    sanitize_string,
    sanitize_record
)

@pytest.fixture
def valid_patient_data():
    """Valid patient data fixture."""
    return {
        'patient_id': 'P123456',
        'first_name': 'John',
        'last_name': 'Doe',
        'date_of_birth': '1980-01-01',
        'gender': 'M',
        'email': 'john.doe@example.com'
    }

@pytest.fixture
def valid_admission_data():
    """Valid admission data fixture."""
    return {
        'admission_id': 'A123456',
        'patient_id': 'P123456',
        'admission_date': '2025-05-09T10:00:00',
        'ward': 'Cardiology',
        'bed_number': 'C101',
        'status': 'Active'
    }

@pytest.fixture
def valid_test_data():
    """Valid test data fixture."""
    return {
        'test_id': 'T123456',
        'patient_id': 'P123456',
        'admission_id': 'A123456',
        'test_type': 'Blood Test',
        'test_date': '2025-05-09T10:00:00',
        'result': 'Normal',
        'status': 'Completed',
        'lab_location': 'Main Lab'
    }

def test_patient_data_validation(valid_patient_data):
    """Test patient data validation."""
    # Test valid data
    patient = PatientData(**valid_patient_data)
    assert patient.patient_id == valid_patient_data['patient_id']

    # Test invalid patient ID
    with pytest.raises(ValidationError):
        PatientData(**{**valid_patient_data, 'patient_id': '123'})

    # Test invalid date of birth
    with pytest.raises(ValidationError):
        PatientData(**{**valid_patient_data, 'date_of_birth': 'invalid-date'})

    # Test future date of birth
    future_date = (datetime.now().date() + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    with pytest.raises(ValidationError):
        PatientData(**{**valid_patient_data, 'date_of_birth': future_date})

    # Test invalid gender
    with pytest.raises(ValidationError):
        PatientData(**{**valid_patient_data, 'gender': 'X'})

    # Test invalid email
    with pytest.raises(ValidationError):
        PatientData(**{**valid_patient_data, 'email': 'invalid-email'})

def test_admission_data_validation(valid_admission_data):
    """Test admission data validation."""
    # Test valid data
    admission = AdmissionData(**valid_admission_data)
    assert admission.admission_id == valid_admission_data['admission_id']

    # Test invalid admission ID
    with pytest.raises(ValidationError):
        AdmissionData(**{**valid_admission_data, 'admission_id': '123'})

    # Test invalid date format
    with pytest.raises(ValidationError):
        AdmissionData(**{**valid_admission_data, 'admission_date': 'invalid-date'})

    # Test invalid status
    with pytest.raises(ValidationError):
        AdmissionData(**{**valid_admission_data, 'status': 'Invalid'})

def test_test_data_validation(valid_test_data):
    """Test test data validation."""
    # Test valid data
    test = TestData(**valid_test_data)
    assert test.test_id == valid_test_data['test_id']

    # Test invalid test ID
    with pytest.raises(ValidationError):
        TestData(**{**valid_test_data, 'test_id': '123'})

    # Test invalid date format
    with pytest.raises(ValidationError):
        TestData(**{**valid_test_data, 'test_date': 'invalid-date'})

    # Test invalid status
    with pytest.raises(ValidationError):
        TestData(**{**valid_test_data, 'status': 'Invalid'})

def test_csv_validation():
    """Test CSV data validation."""
    # Create test DataFrame
    data = pd.DataFrame([
        {'col1': 'value1', 'col2': 'value2'},
        {'col1': 'value3', 'col2': None}
    ])

    # Test missing columns
    errors = validate_csv_data(data, ['col1', 'col2', 'col3'])
    assert len(errors) == 1
    assert 'missing_columns' in errors[0]['type']

    # Test null values
    errors = validate_csv_data(data, ['col1', 'col2'])
    assert len(errors) == 1
    assert 'null_values' in errors[0]['type']

def test_record_validation(valid_patient_data, valid_admission_data, valid_test_data):
    """Test record validation functions."""
    # Test patient record validation
    assert len(validate_patient_record(valid_patient_data)) == 0
    assert len(validate_patient_record({'invalid': 'data'})) > 0

    # Test admission record validation
    assert len(validate_admission_record(valid_admission_data)) == 0
    assert len(validate_admission_record({'invalid': 'data'})) > 0

    # Test test record validation
    assert len(validate_test_record(valid_test_data)) == 0
    assert len(validate_test_record({'invalid': 'data'})) > 0

def test_request_params_validation():
    """Test request parameters validation."""
    params = {
        'required1': 'value1',
        'required2': 'value2',
        'optional1': '123'
    }

    # Test valid params
    is_valid, errors = validate_request_params(
        params,
        required=['required1', 'required2'],
        optional={'optional1': str.isdigit}
    )
    assert is_valid
    assert len(errors) == 0

    # Test missing required param
    is_valid, errors = validate_request_params(
        params,
        required=['required1', 'missing']
    )
    assert not is_valid
    assert len(errors) == 1

    # Test invalid optional param
    params['optional1'] = 'abc'
    is_valid, errors = validate_request_params(
        params,
        required=['required1'],
        optional={'optional1': str.isdigit}
    )
    assert not is_valid
    assert len(errors) == 1

def test_string_sanitization():
    """Test string sanitization."""
    # Test control character removal
    assert sanitize_string('test\x00string') == 'teststring'
    
    # Test non-printable character removal
    assert sanitize_string('test\x7Fstring') == 'teststring'
    
    # Test normal string
    assert sanitize_string('normal string') == 'normal string'
    
    # Test None value
    assert sanitize_string(None) is None

def test_record_sanitization():
    """Test record sanitization."""
    record = {
        'string_field': 'test\x00string',
        'int_field': 123,
        'none_field': None,
        'nested_string': 'test\x7Fstring'
    }

    sanitized = sanitize_record(record)
    assert sanitized['string_field'] == 'teststring'
    assert sanitized['int_field'] == 123
    assert sanitized['none_field'] is None
    assert sanitized['nested_string'] == 'teststring'