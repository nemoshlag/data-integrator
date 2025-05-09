"""Tests for HTTP utilities."""
import pytest
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
import json

from src.utils.http import (
    HttpError,
    create_response,
    create_error_response,
    parse_request_body,
    get_query_params,
    handle_cors_preflight,
    api_handler
)

class TestRequestModel(BaseModel):
    """Test model for request validation."""
    name: str
    age: int
    email: Optional[str] = None

@pytest.fixture
def mock_event():
    """Create a mock Lambda event."""
    return {
        'body': json.dumps({
            'name': 'Test User',
            'age': 30,
            'email': 'test@example.com'
        }),
        'queryStringParameters': {
            'filter': 'active',
            'limit': '10'
        },
        'headers': {
            'Content-Type': 'application/json'
        },
        'httpMethod': 'POST'
    }

def test_create_response():
    """Test creating standard responses."""
    # Test basic response
    response = create_response(
        status_code=200,
        body={'message': 'Success'}
    )
    
    assert response['statusCode'] == 200
    assert 'headers' in response
    assert 'Content-Type' in response['headers']
    assert 'Access-Control-Allow-Origin' in response['headers']
    
    body = json.loads(response['body'])
    assert body['message'] == 'Success'
    
    # Test response with custom headers
    response = create_response(
        status_code=201,
        body={'id': '123'},
        headers={'Custom-Header': 'Value'}
    )
    
    assert response['statusCode'] == 201
    assert response['headers']['Custom-Header'] == 'Value'
    assert 'Access-Control-Allow-Origin' in response['headers']

def test_create_error_response():
    """Test creating error responses."""
    response = create_error_response(
        message='Invalid input',
        status_code=400,
        error_code='VALIDATION_ERROR',
        details={'field': 'name'}
    )
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'error' in body
    assert body['error']['message'] == 'Invalid input'
    assert body['error']['code'] == 'VALIDATION_ERROR'
    assert body['error']['details'] == {'field': 'name'}
    assert 'timestamp' in body['error']

def test_parse_request_body(mock_event):
    """Test request body parsing and validation."""
    # Test parsing without validation
    body = parse_request_body(mock_event)
    assert body['name'] == 'Test User'
    assert body['age'] == 30
    
    # Test parsing with validation
    body = parse_request_body(mock_event, TestRequestModel)
    assert isinstance(body, TestRequestModel)
    assert body.name == 'Test User'
    assert body.age == 30
    
    # Test invalid JSON
    with pytest.raises(HttpError) as exc_info:
        parse_request_body({'body': 'invalid json'})
    assert exc_info.value.status_code == 400
    
    # Test validation error
    invalid_event = {
        'body': json.dumps({
            'name': 'Test',
            'age': 'invalid'  # Should be int
        })
    }
    with pytest.raises(HttpError) as exc_info:
        parse_request_body(invalid_event, TestRequestModel)
    assert exc_info.value.status_code == 422
    assert 'VALIDATION_ERROR' in exc_info.value.error_code

def test_get_query_params(mock_event):
    """Test query parameter handling."""
    # Test getting all params
    params = get_query_params(mock_event)
    assert params['filter'] == 'active'
    assert params['limit'] == '10'
    
    # Test required params
    params = get_query_params(mock_event, required=['filter'])
    assert params['filter'] == 'active'
    
    # Test missing required params
    with pytest.raises(HttpError) as exc_info:
        get_query_params(mock_event, required=['missing'])
    assert exc_info.value.status_code == 400
    assert 'missing' in str(exc_info.value.details)

def test_handle_cors_preflight():
    """Test CORS preflight handling."""
    # Test OPTIONS request
    response = handle_cors_preflight({'httpMethod': 'OPTIONS'})
    assert response['statusCode'] == 204
    assert 'Access-Control-Allow-Origin' in response['headers']
    
    # Test non-OPTIONS request
    response = handle_cors_preflight({'httpMethod': 'GET'})
    assert response is None

@pytest.mark.asyncio
async def test_api_handler():
    """Test API handler decorator."""
    # Test successful handler
    @api_handler(validator=TestRequestModel)
    async def test_handler(event, context):
        return {'message': 'Success', 'data': event['parsed_body'].dict()}
    
    response = await test_handler(mock_event, None)
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['message'] == 'Success'
    assert body['data']['name'] == 'Test User'
    
    # Test handler with error
    @api_handler()
    async def error_handler(event, context):
        raise HttpError('Test error', 400)
    
    response = await error_handler(mock_event, None)
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['error']['message'] == 'Test error'
    
    # Test handler with unexpected error
    @api_handler()
    async def unexpected_error_handler(event, context):
        raise ValueError('Unexpected error')
    
    response = await unexpected_error_handler(mock_event, None)
    assert response['statusCode'] == 500
    body = json.loads(response['body'])
    assert 'Internal server error' in body['error']['message']

def test_http_error():
    """Test HttpError class."""
    error = HttpError(
        message='Test error',
        status_code=400,
        error_code='TEST_ERROR',
        details={'test': 'detail'}
    )
    
    assert str(error) == 'Test error'
    assert error.status_code == 400
    assert error.error_code == 'TEST_ERROR'
    assert error.details == {'test': 'detail'}