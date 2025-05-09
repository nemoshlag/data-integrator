"""Unit tests for health check endpoint."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import json

from src.functions.api.health import handle, check_dynamodb_tables

@pytest.fixture
def mock_tables():
    """Mock DynamoDB tables."""
    tables = {
        'patients': MagicMock(),
        'admissions': MagicMock(),
        'tests': MagicMock()
    }
    for table in tables.values():
        table.table = MagicMock()
        table.table.scan = MagicMock(return_value={'Items': []})
    return tables

def test_check_dynamodb_tables_all_healthy(mock_tables):
    """Test checking DynamoDB tables when all are healthy."""
    with patch('src.functions.api.health.patients_table', mock_tables['patients']), \
         patch('src.functions.api.health.admissions_table', mock_tables['admissions']), \
         patch('src.functions.api.health.tests_table', mock_tables['tests']):
        
        result = check_dynamodb_tables()
        
        assert result['patients'] is True
        assert result['admissions'] is True
        assert result['tests'] is True

def test_check_dynamodb_tables_with_failure(mock_tables):
    """Test checking DynamoDB tables when one fails."""
    # Make admissions table fail
    mock_tables['admissions'].table.scan.side_effect = Exception("Connection error")
    
    with patch('src.functions.api.health.patients_table', mock_tables['patients']), \
         patch('src.functions.api.health.admissions_table', mock_tables['admissions']), \
         patch('src.functions.api.health.tests_table', mock_tables['tests']):
        
        result = check_dynamodb_tables()
        
        assert result['patients'] is True
        assert result['admissions'] is False
        assert result['tests'] is True

def test_health_check_success(mock_tables):
    """Test successful health check."""
    event = {}
    
    with patch('src.functions.api.health.patients_table', mock_tables['patients']), \
         patch('src.functions.api.health.admissions_table', mock_tables['admissions']), \
         patch('src.functions.api.health.tests_table', mock_tables['tests']):
        
        response = handle(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'healthy'
        assert 'timestamp' in body
        assert body['services']['dynamodb']['status'] == 'healthy'
        assert all(body['services']['dynamodb']['tables'].values())

def test_health_check_degraded(mock_tables):
    """Test health check with degraded service."""
    event = {}
    # Make a table fail
    mock_tables['admissions'].table.scan.side_effect = Exception("Connection error")
    
    with patch('src.functions.api.health.patients_table', mock_tables['patients']), \
         patch('src.functions.api.health.admissions_table', mock_tables['admissions']), \
         patch('src.functions.api.health.tests_table', mock_tables['tests']):
        
        response = handle(event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['status'] == 'degraded'
        assert body['services']['dynamodb']['status'] == 'degraded'
        assert not body['services']['dynamodb']['tables']['admissions']

def test_health_check_complete_failure(mock_tables):
    """Test health check when all services fail."""
    event = {}
    # Make all tables fail
    for table in mock_tables.values():
        table.table.scan.side_effect = Exception("Connection error")
    
    with patch('src.functions.api.health.patients_table', mock_tables['patients']), \
         patch('src.functions.api.health.admissions_table', mock_tables['admissions']), \
         patch('src.functions.api.health.tests_table', mock_tables['tests']):
        
        response = handle(event, None)
        
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['status'] == 'degraded'
        assert body['services']['dynamodb']['status'] == 'degraded'
        assert not any(body['services']['dynamodb']['tables'].values())

def test_health_check_error_handling():
    """Test health check error handling."""
    event = {}
    
    with patch('src.functions.api.health.check_dynamodb_tables', 
              side_effect=Exception("Unexpected error")):
        
        response = handle(event, None)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert 'error' in body