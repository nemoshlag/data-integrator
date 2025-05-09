"""HTTP response utilities for Lambda functions."""
import json
from typing import Any, Dict, Optional, Union, Tuple, Callable, TypeVar
from datetime import datetime
import traceback
from functools import wraps
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser import parse_qs, BaseModel, ValidationError

from .logging import get_logger
from .config import get_config

logger = get_logger('http')
config = get_config()

# Type variables for generic functions
T = TypeVar('T')

# HTTP Status Codes
HTTP_200_OK = 200
HTTP_201_CREATED = 201
HTTP_204_NO_CONTENT = 204
HTTP_400_BAD_REQUEST = 400
HTTP_401_UNAUTHORIZED = 401
HTTP_403_FORBIDDEN = 403
HTTP_404_NOT_FOUND = 404
HTTP_422_VALIDATION_ERROR = 422
HTTP_500_SERVER_ERROR = 500

class HttpError(Exception):
    """Custom HTTP error class."""
    def __init__(
        self, 
        message: str, 
        status_code: int = HTTP_400_BAD_REQUEST, 
        error_code: str = None,
        details: Optional[Dict] = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}

def create_error_response(
    message: str,
    status_code: int = HTTP_400_BAD_REQUEST,
    error_code: str = None,
    details: Optional[Dict] = None
) -> Dict[str, Any]:
    """Create an error response."""
    body = {
        'error': {
            'message': message,
            'code': error_code,
            'details': details or {},
            'timestamp': datetime.utcnow().isoformat()
        }
    }
    return create_response(status_code=status_code, body=body)

def create_response(
    status_code: int = HTTP_200_OK,
    body: Optional[Union[Dict, list, str]] = None,
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Create a standardized HTTP response."""
    base_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': config.environment.CORS_ORIGIN,
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Amz-Date,X-Api-Key'
    }

    if headers:
        base_headers.update(headers)

    response = {
        'statusCode': status_code,
        'headers': base_headers
    }

    if body is not None:
        if isinstance(body, (dict, list)):
            response['body'] = json.dumps(body)
        else:
            response['body'] = str(body)

    return response

def parse_request_body(event: Dict[str, Any], model: Optional[type[BaseModel]] = None) -> Any:
    """Parse and optionally validate request body."""
    try:
        body = event.get('body', '{}')
        if isinstance(body, str):
            body = json.loads(body)
        
        if model:
            return model.parse_obj(body)
        return body
    except json.JSONDecodeError:
        raise HttpError('Invalid JSON in request body', HTTP_400_BAD_REQUEST)
    except ValidationError as e:
        raise HttpError(
            'Validation error',
            HTTP_422_VALIDATION_ERROR,
            'VALIDATION_ERROR',
            {'errors': e.errors()}
        )

def get_query_params(event: Dict[str, Any], required: Optional[list[str]] = None) -> Dict[str, Any]:
    """Get and validate query parameters."""
    params = event.get('queryStringParameters', {}) or {}
    if required:
        missing = [param for param in required if param not in params]
        if missing:
            raise HttpError(
                'Missing required query parameters',
                HTTP_400_BAD_REQUEST,
                'MISSING_PARAMS',
                {'missing': missing}
            )
    return params

def handle_cors_preflight(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Handle CORS preflight requests."""
    if event.get('httpMethod') == 'OPTIONS':
        return create_response(HTTP_204_NO_CONTENT)
    return None

def api_handler(validator: Optional[type[BaseModel]] = None):
    """Decorator for API Lambda handlers."""
    def decorator(handler: Callable) -> Callable:
        @wraps(handler)
        async def wrapper(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
            try:
                # Handle CORS preflight
                cors_response = handle_cors_preflight(event)
                if cors_response:
                    return cors_response

                # Parse and validate request if needed
                if validator and event.get('body'):
                    event['parsed_body'] = parse_request_body(event, validator)

                # Execute handler
                response = await handler(event, context)
                return response if isinstance(response, dict) else create_response(body=response)

            except HttpError as e:
                logger.warning(
                    f"HTTP error in {handler.__name__}",
                    error=str(e),
                    status_code=e.status_code,
                    error_code=e.error_code
                )
                return create_error_response(
                    str(e),
                    e.status_code,
                    e.error_code,
                    e.details
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error in {handler.__name__}",
                    error=str(e),
                    traceback=traceback.format_exc()
                )
                return create_error_response(
                    'Internal server error',
                    HTTP_500_SERVER_ERROR,
                    'INTERNAL_ERROR'
                )
        return wrapper
    return decorator