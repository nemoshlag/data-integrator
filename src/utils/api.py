"""API utility functions."""
from typing import Dict, Any, Optional
import json
from datetime import datetime

from .constants import CORS_HEADERS

def create_response(
    status_code: int = 200,
    body: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None
) -> Dict[str, Any]:
    """Create an API Gateway response with CORS headers."""
    response_body = {
        'timestamp': datetime.now().isoformat()
    }

    if body is not None:
        response_body.update(body)
    
    if error is not None:
        response_body['error'] = error

    return {
        'statusCode': status_code,
        'headers': CORS_HEADERS,
        'body': json.dumps(response_body)
    }

def create_error_response(
    error_message: str,
    error_code: str,
    status_code: int = 500
) -> Dict[str, Any]:
    """Create an error response."""
    return create_response(
        status_code=status_code,
        body={
            'error': {
                'message': error_message,
                'code': error_code
            }
        }
    )

def parse_query_params(event: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
    """Parse and validate query parameters with defaults."""
    params = event.get('queryStringParameters', {}) or {}
    result = {}

    for key, default_value in defaults.items():
        value = params.get(key, default_value)
        if isinstance(default_value, int):
            try:
                result[key] = int(value)
            except (TypeError, ValueError):
                result[key] = default_value
        else:
            result[key] = value

    return result

def handle_options_request() -> Dict[str, Any]:
    """Handle CORS preflight request."""
    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': ''
    }

def validate_request(
    required_params: Dict[str, Any],
    provided_params: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Validate request parameters."""
    missing_params = []
    invalid_params = []

    for param, validator in required_params.items():
        if param not in provided_params:
            missing_params.append(param)
        elif not validator(provided_params[param]):
            invalid_params.append(param)

    if missing_params or invalid_params:
        return create_error_response(
            error_message=f"Invalid request parameters. Missing: {missing_params}, Invalid: {invalid_params}",
            error_code='INVALID_PARAMETERS',
            status_code=400
        )

    return None