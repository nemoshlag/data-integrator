"""Error handling utilities for the application."""
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import traceback
import json

from .logging import get_logger

logger = get_logger('errors')

class BaseError(Exception):
    """Base error class for application errors."""
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format."""
        return {
            'error': {
                'code': self.error_code,
                'message': self.message,
                'details': self.details,
                'timestamp': self.timestamp
            }
        }

    def log_error(self, include_traceback: bool = True) -> None:
        """Log error details."""
        error_info = {
            'error_code': self.error_code,
            'message': self.message,
            'details': self.details
        }
        if include_traceback:
            error_info['traceback'] = traceback.format_exc()
        
        logger.error(
            f"Application error: {self.error_code}",
            extra=error_info
        )

class ValidationError(BaseError):
    """Validation error."""
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code='VALIDATION_ERROR',
            status_code=400,
            details=details
        )

class DatabaseError(BaseError):
    """Database operation error."""
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code='DATABASE_ERROR',
            status_code=500,
            details=details
        )

class NotFoundError(BaseError):
    """Resource not found error."""
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code='NOT_FOUND',
            status_code=404,
            details=details
        )

class ProcessingError(BaseError):
    """Data processing error."""
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code='PROCESSING_ERROR',
            status_code=500,
            details=details
        )

class ConfigurationError(BaseError):
    """Configuration error."""
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code='CONFIGURATION_ERROR',
            status_code=500,
            details=details
        )

def handle_error(
    error: Union[BaseError, Exception],
    include_details: bool = True
) -> Dict[str, Any]:
    """Handle and format error response."""
    if isinstance(error, BaseError):
        error.log_error()
        response = error.to_dict()
        status_code = error.status_code
    else:
        logger.error(
            f"Unhandled error: {str(error)}",
            extra={'traceback': traceback.format_exc()}
        )
        response = {
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An unexpected error occurred',
                'timestamp': datetime.utcnow().isoformat()
            }
        }
        if include_details:
            response['error']['details'] = {
                'type': type(error).__name__,
                'message': str(error)
            }
        status_code = 500

    return {
        'statusCode': status_code,
        'body': json.dumps(response),
        'headers': {
            'Content-Type': 'application/json'
        }
    }

def format_validation_errors(errors: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Format validation errors for response."""
    return {
        'error': {
            'code': 'VALIDATION_ERROR',
            'message': 'Validation failed',
            'details': {
                'validation_errors': errors
            },
            'timestamp': datetime.utcnow().isoformat()
        }
    }

def format_database_errors(operation: str, details: Dict[str, Any]) -> Dict[str, Any]:
    """Format database operation errors."""
    return {
        'error': {
            'code': 'DATABASE_ERROR',
            'message': f'Database {operation} failed',
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        }
    }

def format_processing_errors(
    source: str,
    errors: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Format data processing errors."""
    return {
        'error': {
            'code': 'PROCESSING_ERROR',
            'message': f'Error processing {source}',
            'details': {
                'processing_errors': errors
            },
            'timestamp': datetime.utcnow().isoformat()
        }
    }