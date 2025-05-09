"""Unit tests for get_patients API handler."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from src.functions.api.get_patients import (
    get_patient_details,
    get_patients_without_tests,
    handle
)
from src.lib.models import Patient, Admission

@pytest.fixture
def mock_patient():
    """Create a mock patient."""
    return Patient(
        patient_id="P123",
        first_name="John",
        last_name="Doe",
        date_of_birth="1980-01-01",
        gender="M",
        updated_at=datetime.now().isoformat()
    )

@pytest.fixture
def mock_admission():
    """Create a mock admission."""
    return Admission(
        patient_id="P123",
        admission_id="A456",
        admission_date=datetime.now().isoformat(),
        ward="Cardiology",
        bed_number="C1",
        status="Active",
        last_test_date=(datetime.now() - timedelta(hours=49)).isoformat(),
        hours_since_test=49,
        updated_at=datetime.now().isoformat()
    )

def test_get_patient_details(mock_patient):
    """Test getting patient details."""
    with patch('src.lib.dynamodb.patients_table.get_item', return_value=mock_patient):
        result = get_patient_details(mock_patient.patient_id)
        
        assert result is not None
        assert result['patientId'] == mock_patient.patient_id
        assert result['firstName'] == mock_patient.first_name
        assert result['lastName'] == mock_patient.last_name

def test_get_patient_details_not_found():
    """Test getting non-existent patient details."""
    with patch('src.lib.dynamodb.patients_table.get_item', return_value=None):
        result = get_patient_details("NONEXISTENT")
        assert result is None

def test_get_patients_without_tests(mock_admission):
    """Test getting patients without tests."""
    with patch('src.lib.dynamodb.admissions_table.query_index', return_value=[mock_admission]), \
         patch('src.functions.api.get_patients.get_patient_details', return_value={
             'patientId': mock_admission.patient_id,
             'firstName': 'John',
             'lastName': 'Doe',
             'dateOfBirth': '1980-01-01',
             'gender': 'M'
         }):
        
        result = get_patients_without_tests(hours=48)
        
        assert len(result) == 1
        assert result[0]['patientId'] == mock_admission.patient_id
        assert result[0]['admissionId'] == mock_admission.admission_id
        assert result[0]['ward'] == mock_admission.ward

def test_get_patients_without_tests_ward_filter(mock_admission):
    """Test filtering patients by ward."""
    with patch('src.lib.dynamodb.admissions_table.query_index', return_value=[mock_admission]), \
         patch('src.functions.api.get_patients.get_patient_details', return_value={
             'patientId': mock_admission.patient_id,
             'firstName': 'John',
             'lastName': 'Doe',
             'dateOfBirth': '1980-01-01',
             'gender': 'M'
         }):
        
        # Test matching ward
        result = get_patients_without_tests(hours=48, ward='Cardiology')
        assert len(result) == 1
        
        # Test non-matching ward
        result = get_patients_without_tests(hours=48, ward='Neurology')
        assert len(result) == 0

def test_handler_success(mock_admission):
    """Test successful API handler execution."""
    event = {
        'queryStringParameters': {
            'hours': '48',
            'ward': 'Cardiology'
        }
    }
    
    with patch('src.functions.api.get_patients.get_patients_without_tests', 
              return_value=[{
                  'patientId': mock_admission.patient_id,
                  'admissionId': mock_admission.admission_id,
                  'ward': mock_admission.ward,
                  'firstName': 'John',
                  'lastName': 'Doe'
              }]):
        
        result = handle(event, None)
        
        assert result['statusCode'] == 200
        body = eval(result['body'])  # Convert string to dict
        assert len(body['patients']) == 1
        assert body['totalCount'] == 1

def test_handler_no_patients():
    """Test handler when no patients need attention."""
    event = {
        'queryStringParameters': {
            'hours': '48'
        }
    }
    
    with patch('src.functions.api.get_patients.get_patients_without_tests', return_value=[]):
        result = handle(event, None)
        
        assert result['statusCode'] == 200
        body = eval(result['body'])
        assert len(body['patients']) == 0
        assert body['totalCount'] == 0

def test_handler_error():
    """Test handler error handling."""
    event = {
        'queryStringParameters': {
            'hours': '48'
        }
    }
    
    with patch('src.functions.api.get_patients.get_patients_without_tests', 
              side_effect=Exception('Database error')):
        
        result = handle(event, None)
        
        assert result['statusCode'] == 500
        body = eval(result['body'])
        assert 'error' in body

def test_handler_options_request():
    """Test CORS OPTIONS request handling."""
    event = {
        'httpMethod': 'OPTIONS'
    }
    
    result = handle(event, None)
    
    assert result['statusCode'] == 200
    assert 'Access-Control-Allow-Origin' in result['headers']