"""Integration tests for health check endpoint."""
import pytest
import json
from datetime import datetime
import boto3

from src.functions.api.health import handle
from ..utils import create_test_event

@pytest.fixture(scope='function')
def health_tables(test_tables):
    """Set up tables for health check testing."""
    # Add some test data to verify table access
    test_tables['patients'].put_item(
        Item={
            'PK': 'PATIENT#TEST',
            'SK': 'METADATA',
            'patient_id': 'TEST',
            'first_name': 'Test',
            'last_name': 'Patient',
            'date_of_birth': '2000-01-01',
            'gender': 'M'
        }
    )
    
    test_tables['admissions'].put_item(
        Item={
            'PK': 'PATIENT#TEST',
            'SK': 'ADMISSION#TEST',
            'patient_id': 'TEST',
            'admission_id': 'TEST',
            'admission_date': datetime.now().isoformat(),
            'ward': 'TEST',
            'bed_number': 'TEST',
            'status': 'Active',
            'hours_since_test': 0
        }
    )
    
    return test_tables

def test_health_check_integration(health_tables):
    """Test health check with actual DynamoDB tables."""
    event = create_test_event(path='/health')
    
    response = handle(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['status'] == 'healthy'
    assert 'timestamp' in body
    assert body['services']['dynamodb']['status'] == 'healthy'
    assert all(body['services']['dynamodb']['tables'].values())

def test_health_check_table_access(health_tables):
    """Test health check can actually access table data."""
    event = create_test_event(path='/health')
    
    # Try to read from each table before health check
    for table in health_tables.values():
        response = table.scan(Limit=1)
        assert 'Items' in response
    
    response = handle(event, None)
    assert response['statusCode'] == 200

def test_health_check_with_table_deletion(health_tables, dynamodb_resource):
    """Test health check when a table is deleted."""
    event = create_test_event(path='/health')
    
    # Delete one table
    health_tables['patients'].delete()
    
    response = handle(event, None)
    
    assert response['statusCode'] == 503
    body = json.loads(response['body'])
    assert body['status'] == 'degraded'
    assert body['services']['dynamodb']['status'] == 'degraded'
    assert not body['services']['dynamodb']['tables']['patients']
    assert body['services']['dynamodb']['tables']['admissions']
    assert body['services']['dynamodb']['tables']['tests']

def test_health_check_cors_headers(health_tables):
    """Test that health check returns proper CORS headers."""
    event = create_test_event(
        path='/health',
        headers={
            'Origin': 'http://localhost:3000'
        }
    )
    
    response = handle(event, None)
    
    assert response['statusCode'] == 200
    assert 'headers' in response
    assert 'Access-Control-Allow-Origin' in response['headers']
    assert 'Access-Control-Allow-Credentials' in response['headers']

def test_health_check_performance(health_tables):
    """Test health check response time."""
    event = create_test_event(path='/health')
    
    start_time = datetime.now()
    response = handle(event, None)
    end_time = datetime.now()
    
    duration = (end_time - start_time).total_seconds()
    
    # Health check should complete in under 1 second
    assert duration < 1.0
    assert response['statusCode'] == 200