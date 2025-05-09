"""Tests for logging utility."""
import pytest
import json
import logging
from unittest.mock import MagicMock, patch
from aws_lambda_powertools import Logger

from src.utils.logging import (
    ApplicationLogger,
    get_logger,
    log_function_call,
    setup_monitoring_logger,
    setup_api_logger,
    log_event
)

@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    with patch('src.utils.logging.config') as mock:
        mock.environment.POWERTOOLS_SERVICE_NAME = 'test-service'
        mock.environment.LOG_LEVEL = 'INFO'
        yield mock

@pytest.fixture
def mock_local_env():
    """Mock local environment setting."""
    with patch('src.utils.logging.is_local_environment', return_value=True):
        yield

@pytest.fixture
def mock_prod_env():
    """Mock production environment setting."""
    with patch('src.utils.logging.is_local_environment', return_value=False):
        yield

@pytest.fixture
def capture_logs(caplog):
    """Capture logs for testing."""
    caplog.set_level(logging.INFO)
    return caplog

def test_logger_initialization(mock_config):
    """Test logger initialization."""
    logger = ApplicationLogger('test')
    assert logger.service == 'test'
    assert isinstance(logger.logger, Logger)

def test_local_formatting(mock_config, mock_local_env, capture_logs):
    """Test local environment log formatting."""
    logger = ApplicationLogger()
    logger.info("Test message", extra_field="test")
    
    assert "Test message" in capture_logs.text
    assert "extra_field" in capture_logs.text
    assert "test" in capture_logs.text

def test_production_formatting(mock_config, mock_prod_env, capture_logs):
    """Test production environment log formatting."""
    logger = ApplicationLogger()
    logger.info("Test message", extra_field="test")
    
    log_record = json.loads(capture_logs.records[0].message)
    assert log_record['message'] == "Test message"
    assert log_record['extra_field'] == "test"
    assert 'service' in log_record

def test_log_levels(mock_config, capture_logs):
    """Test different log levels."""
    logger = ApplicationLogger()
    
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    assert "Debug message" not in capture_logs.text  # Default level is INFO
    assert "Info message" in capture_logs.text
    assert "Warning message" in capture_logs.text
    assert "Error message" in capture_logs.text

def test_error_logging_with_exception(mock_config, capture_logs):
    """Test error logging with exception information."""
    logger = ApplicationLogger()
    
    try:
        raise ValueError("Test error")
    except ValueError:
        logger.error("An error occurred")
    
    assert "An error occurred" in capture_logs.text
    assert "ValueError" in capture_logs.text
    assert "Test error" in capture_logs.text

@log_function_call()
def sample_function(arg1, arg2=None):
    """Sample function for testing decorator."""
    if arg2 is None:
        raise ValueError("arg2 cannot be None")
    return arg1 + arg2

def test_log_function_call_decorator(mock_config, capture_logs):
    """Test function call logging decorator."""
    # Test successful call
    result = sample_function(1, 2)
    assert result == 3
    assert "Calling sample_function" in capture_logs.text
    assert "Completed sample_function" in capture_logs.text
    
    # Test error case
    with pytest.raises(ValueError):
        sample_function(1)
    assert "Error in sample_function" in capture_logs.text
    assert "ValueError" in capture_logs.text

def test_setup_monitoring_logger(mock_config):
    """Test monitoring logger setup."""
    logger = setup_monitoring_logger()
    assert logger.service == 'monitoring'
    assert isinstance(logger.logger, Logger)

def test_setup_api_logger(mock_config):
    """Test API logger setup."""
    logger = setup_api_logger()
    assert logger.service == 'api'
    assert isinstance(logger.logger, Logger)

def test_log_event(mock_config, capture_logs):
    """Test Lambda event logging."""
    event = {'test': 'event'}
    context = MagicMock(
        function_name='test-function',
        function_version='1',
        memory_limit_in_mb=128,
        get_remaining_time_in_millis=lambda: 1000
    )
    
    log_event(event, context)
    
    assert 'Lambda event received' in capture_logs.text
    assert 'test-function' in capture_logs.text
    assert 'test' in capture_logs.text
    assert 'event' in capture_logs.text

def test_get_logger_singleton(mock_config):
    """Test logger singleton pattern."""
    logger1 = get_logger('test')
    logger2 = get_logger('test')
    
    assert logger1.service == logger2.service
    assert logger1.logger is not logger2.logger  # Each instance should have its own logger

def test_logger_with_structured_fields(mock_config, capture_logs):
    """Test logging with structured fields."""
    logger = ApplicationLogger()
    
    test_data = {
        'user_id': '123',
        'action': 'test',
        'metadata': {'key': 'value'}
    }
    
    logger.info(
        "User action",
        **test_data
    )
    
    log_record = capture_logs.records[0]
    assert "User action" in str(log_record.message)
    assert "user_id" in str(log_record.message)
    assert "metadata" in str(log_record.message)