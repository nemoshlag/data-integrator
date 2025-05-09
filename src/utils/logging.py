"""Logging configuration for the application."""
import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional
from aws_lambda_powertools import Logger
from aws_lambda_powertools.logging import correlation_paths
from functools import wraps
import traceback
import sys

from .config import get_config, is_local_environment

# Initialize configuration
config = get_config()

class ApplicationLogger:
    """Custom logger for the application."""

    def __init__(self, service: str = None):
        """Initialize logger with service name."""
        self.service = service or config.environment.POWERTOOLS_SERVICE_NAME
        self.logger = Logger(
            service=self.service,
            level=config.environment.LOG_LEVEL,
            use_rfc3339=True,
            sample_rate=1 if is_local_environment() else 0.1
        )
        
        # Add custom formatting for local development
        if is_local_environment():
            self._setup_local_formatting()

    def _setup_local_formatting(self) -> None:
        """Configure prettier logging for local development."""
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        
        # Remove default handlers and add our custom one
        self.logger.handlers.clear()
        self.logger.addHandler(handler)

    def _format_log_message(self, message: str, additional_fields: Dict[str, Any]) -> str:
        """Format log message with additional fields."""
        if not additional_fields:
            return message

        if is_local_environment():
            # Pretty format for local development
            fields_str = json.dumps(additional_fields, indent=2)
            return f"{message}\nContext: {fields_str}"
        
        # Add fields directly to message for production
        return message

    def info(self, message: str, **kwargs) -> None:
        """Log info level message."""
        self.logger.info(
            self._format_log_message(message, kwargs),
            extra=kwargs
        )

    def error(self, message: str, exc_info: bool = True, **kwargs) -> None:
        """Log error level message."""
        self.logger.error(
            self._format_log_message(message, kwargs),
            exc_info=exc_info,
            extra=kwargs
        )

    def warning(self, message: str, **kwargs) -> None:
        """Log warning level message."""
        self.logger.warning(
            self._format_log_message(message, kwargs),
            extra=kwargs
        )

    def debug(self, message: str, **kwargs) -> None:
        """Log debug level message."""
        self.logger.debug(
            self._format_log_message(message, kwargs),
            extra=kwargs
        )

def get_logger(service: str = None) -> ApplicationLogger:
    """Get or create a logger instance."""
    return ApplicationLogger(service)

def log_function_call(logger: Optional[ApplicationLogger] = None):
    """Decorator to log function calls."""
    def decorator(func):
        _logger = logger or get_logger(func.__module__)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            function_name = func.__name__
            _logger.debug(
                f"Calling {function_name}",
                function=function_name,
                arguments={
                    'args': str(args),
                    'kwargs': str(kwargs)
                }
            )
            
            try:
                result = func(*args, **kwargs)
                _logger.debug(
                    f"Completed {function_name}",
                    function=function_name,
                    status='success'
                )
                return result
            except Exception as e:
                _logger.error(
                    f"Error in {function_name}: {str(e)}",
                    function=function_name,
                    error_type=type(e).__name__,
                    error_details=str(e),
                    traceback=traceback.format_exc()
                )
                raise
        return wrapper
    return decorator

def setup_monitoring_logger():
    """Configure logger for monitoring functions."""
    logger = get_logger('monitoring')
    logger.logger.structure_logs(append=True, correlation_id=correlation_paths.API_GATEWAY_REST)
    return logger

def setup_api_logger():
    """Configure logger for API functions."""
    logger = get_logger('api')
    logger.logger.structure_logs(append=True, correlation_id=correlation_paths.API_GATEWAY_REST)
    return logger

def log_event(event: Dict[str, Any], context: Any = None):
    """Log Lambda event and context."""
    logger = get_logger('lambda')
    logger.debug(
        "Lambda event received",
        event=event,
        context={
            'function_name': context.function_name if context else None,
            'function_version': context.function_version if context else None,
            'memory_limit': context.memory_limit_in_mb if context else None,
            'time_remaining': context.get_remaining_time_in_millis() if context else None
        } if context else {}
    )

# Default logger instance
logger = get_logger()