"""Tests for configuration management."""
import pytest
import os
from pathlib import Path
import yaml
from src.utils.config import (
    load_config,
    get_config,
    get_table_name,
    get_dynamodb_endpoint,
    is_local_environment,
    AppConfig
)

@pytest.fixture
def test_config_file(tmp_path):
    """Create a temporary test configuration file."""
    config_data = {
        'default': {
            'LOG_LEVEL': 'INFO',
            'POWERTOOLS_SERVICE_NAME': 'test-service',
            'POWERTOOLS_TRACE_DISABLED': True
        },
        'test': {
            'STAGE': 'test',
            'AWS_REGION': 'local',
            'DYNAMODB_ENDPOINT': 'http://localhost:8000',
            'DYNAMODB_PREFIX': 'test-prefix',
            'CORS_ORIGIN': 'http://localhost:3000'
        },
        'development': {
            'STAGE': 'dev',
            'AWS_REGION': 'eu-west-1',
            'DYNAMODB_ENDPOINT': 'http://localhost:8000',
            'DYNAMODB_PREFIX': 'dev-prefix',
            'CORS_ORIGIN': 'http://localhost:3000',
            'API_PORT': 4000,
            'SERVERLESS_PORT': 3000
        },
        'production': {
            'STAGE': 'prod',
            'AWS_REGION': 'eu-west-1',
            'DYNAMODB_PREFIX': 'prod-prefix',
            'CORS_ORIGIN': 'https://example.com',
            'LOG_LEVEL': 'WARNING'
        },
        'tables': {
            'patients': {
                'name': '${DYNAMODB_PREFIX}-patients',
                'indexes': []
            },
            'admissions': {
                'name': '${DYNAMODB_PREFIX}-admissions',
                'indexes': [
                    {
                        'name': 'MonitoringIndex',
                        'hash_key': 'status',
                        'range_key': 'hoursSinceTest'
                    }
                ]
            }
        },
        'monitoring': {
            'test_alert_threshold': 48,
            'warning_threshold': 36,
            'check_interval': 60,
            'batch_size': 100
        },
        'api': {
            'rate_limit': 1000,
            'timeout': 30,
            'max_payload_size': 6
        },
        'websocket': {
            'connection_ttl': 7200,
            'message_retention': 24
        },
        'security': {
            'cors_max_age': 7200,
            'api_key_rotation': 90
        }
    }
    
    config_path = tmp_path / 'env.yaml'
    with open(config_path, 'w') as f:
        yaml.dump(config_data, f)
    
    return config_path

def test_load_config_development(test_config_file, monkeypatch):
    """Test loading development configuration."""
    monkeypatch.setenv('STAGE', 'development')
    monkeypatch.setattr('src.utils.config.Path.parent', lambda x: test_config_file.parent)
    
    config = load_config()
    assert isinstance(config, AppConfig)
    assert config.environment.STAGE == 'dev'
    assert config.environment.DYNAMODB_ENDPOINT == 'http://localhost:8000'
    assert config.monitoring.test_alert_threshold == 48

def test_load_config_production(test_config_file, monkeypatch):
    """Test loading production configuration."""
    monkeypatch.setenv('STAGE', 'production')
    monkeypatch.setattr('src.utils.config.Path.parent', lambda x: test_config_file.parent)
    
    config = load_config()
    assert isinstance(config, AppConfig)
    assert config.environment.STAGE == 'prod'
    assert config.environment.DYNAMODB_ENDPOINT is None
    assert config.environment.LOG_LEVEL == 'WARNING'

def test_get_config_singleton(test_config_file, monkeypatch):
    """Test config singleton pattern."""
    monkeypatch.setenv('STAGE', 'test')
    monkeypatch.setattr('src.utils.config.Path.parent', lambda x: test_config_file.parent)
    
    config1 = get_config()
    config2 = get_config()
    assert config1 is config2

def test_get_table_name(test_config_file, monkeypatch):
    """Test getting table names."""
    monkeypatch.setenv('STAGE', 'test')
    monkeypatch.setattr('src.utils.config.Path.parent', lambda x: test_config_file.parent)
    
    assert get_table_name('patients') == 'test-prefix-patients'
    with pytest.raises(ValueError):
        get_table_name('unknown_table')

def test_is_local_environment(test_config_file, monkeypatch):
    """Test local environment detection."""
    monkeypatch.setattr('src.utils.config.Path.parent', lambda x: test_config_file.parent)
    
    monkeypatch.setenv('STAGE', 'development')
    assert is_local_environment() is True
    
    monkeypatch.setenv('STAGE', 'production')
    assert is_local_environment() is False

def test_invalid_config(test_config_file, monkeypatch):
    """Test handling invalid configuration."""
    monkeypatch.setattr('src.utils.config.Path.parent', lambda x: test_config_file.parent)
    
    # Create invalid config
    with open(test_config_file, 'w') as f:
        yaml.dump({'invalid': 'config'}, f)
    
    with pytest.raises(Exception):
        load_config()

def test_config_validation(test_config_file, monkeypatch):
    """Test configuration validation."""
    monkeypatch.setenv('STAGE', 'test')
    monkeypatch.setattr('src.utils.config.Path.parent', lambda x: test_config_file.parent)
    
    config = load_config()
    
    # Test required fields
    assert config.environment.STAGE is not None
    assert config.environment.AWS_REGION is not None
    assert config.environment.DYNAMODB_PREFIX is not None
    
    # Test default values
    assert config.monitoring.batch_size == 100
    assert config.api.timeout == 30
    assert config.websocket.connection_ttl == 7200