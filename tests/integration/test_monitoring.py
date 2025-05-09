"""Integration tests for patient monitoring functionality."""
import pytest
import json
from datetime import datetime, timedelta

from src.functions.api.get_patients import handle as get_patients_handler
from src.functions.monitor_patients.handler import handle as monitor_handler
from ..utils import create_test_event

def test_get_patients_without_tests(test_tables, patient_without_tests):
    """Test getting patients without recent tests."""
    event = create_test_event(
        path='/patients/monitoring',
        query_params={'hours': '48'}
    )
    
    response = get_patients_handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    
    # Should find at least one patient (our test patient)
    assert body['totalCount'] >= 1
    
    # Verify test patient is in results
    patient_found = False
    for patient in body['patients']:
        if patient['patientId'] == patient_without_tests['patient']['patient_id']:
            patient_found = True
            assert patient['ward'] == patient_without_tests['admission']['ward']
            assert patient['hoursSinceTest'] >= 48
    
    assert patient_found, "Test patient not found in results"

def test_get_patients_with_ward_filter(test_tables, patient_without_tests):
    """Test filtering patients by ward."""
    # Test with matching ward
    event = create_test_event(
        path='/patients/monitoring',
        query_params={
            'hours': '48',
            'ward': patient_without_tests['admission']['ward']
        }
    )
    
    response = get_patients_handler(event, None)
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['totalCount'] >= 1
    
    # Test with non-matching ward
    event = create_test_event(
        path='/patients/monitoring',
        query_params={
            'hours': '48',
            'ward': 'NonexistentWard'
        }
    )
    
    response = get_patients_handler(event, None)
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['totalCount'] == 0

async def test_monitor_handler(test_tables, patient_without_tests):
    """Test the monitoring function that sends alerts."""
    event = {}  # Monitor handler doesn't need event data
    
    response = await monitor_handler(event, None)
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    
    # Should find and alert about our test patient
    assert body['patientsAlerted'] >= 1
    assert 'timestamp' in body

def test_monitor_no_alerts_needed(test_tables):
    """Test monitoring when no patients need attention."""
    # Update all admissions to have recent tests
    recent_time = datetime.now().isoformat()
    
    admissions_table = test_tables['admissions']
    response = admissions_table.scan()
    
    for item in response.get('Items', []):
        admissions_table.update_item(
            Key={
                'PK': item['PK'],
                'SK': item['SK']
            },
            UpdateExpression='SET last_test_date = :date, hours_since_test = :hours',
            ExpressionAttributeValues={
                ':date': recent_time,
                ':hours': 0
            }
        )
    
    event = create_test_event(
        path='/patients/monitoring',
        query_params={'hours': '48'}
    )
    
    response = get_patients_handler(event, None)
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['totalCount'] == 0

def test_cors_headers(test_tables):
    """Test that CORS headers are properly set."""
    event = create_test_event(
        path='/patients/monitoring',
        method='OPTIONS'
    )
    
    response = get_patients_handler(event, None)
    
    assert response['statusCode'] == 200
    assert 'Access-Control-Allow-Origin' in response['headers']
    assert 'Access-Control-Allow-Methods' in response['headers']
    assert 'Access-Control-Allow-Headers' in response['headers']

def test_error_handling(test_tables):
    """Test error handling in the API."""
    # Test with invalid hours parameter
    event = create_test_event(
        path='/patients/monitoring',
        query_params={'hours': 'invalid'}
    )
    
    response = get_patients_handler(event, None)
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'error' in body