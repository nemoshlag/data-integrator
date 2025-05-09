"""Configuration management utility."""
import os
from typing import Dict, Any, Optional
import yaml
from pydantic import BaseModel, Field
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class TableIndex(BaseModel):
    """DynamoDB table index configuration."""
    name: str
    hash_key: str
    range_key: Optional[str] = None

class TableConfig(BaseModel):
    """DynamoDB table configuration."""
    name: str
    indexes: list[TableIndex] = []

class MonitoringConfig(BaseModel):
    """Monitoring configuration."""
    test_alert_threshold: int = Field(default=48, ge=1)
    warning_threshold: int = Field(default=36, ge=1)
    check_interval: int = Field(default=60, ge=10)
    batch_size: int = Field(default=100, ge=1, le=1000)

class ApiConfig(BaseModel):
    """API configuration."""
    rate_limit: int = Field(default=1000, ge=1)
    timeout: int = Field(default=30, ge=1, le=900)
    max_payload_size: int = Field(default=6, ge=1, le=10)

class WebSocketConfig(BaseModel):
    """WebSocket configuration."""
    connection_ttl: int = Field(default=7200, ge=60)
    message_retention: int = Field(default=24, ge=1)

class SecurityConfig(BaseModel):
    """Security configuration."""
    cors_max_age: int = Field(default=7200, ge=0)
    api_key_rotation: int = Field(default=90, ge=1)

class EnvironmentConfig(BaseModel):
    """Environment-specific configuration."""
    STAGE: str
    AWS_REGION: str
    LOG_LEVEL: str = 'INFO'
    DYNAMODB_ENDPOINT: Optional[str] = None
    DYNAMODB_PREFIX: str
    CORS_ORIGIN: str
    POWERTOOLS_SERVICE_NAME: str = 'hospital-data-integrator'
    POWERTOOLS_TRACE_DISABLED: bool = True
    API_PORT: Optional[int] = None
    SERVERLESS_PORT: Optional[int] = None

class AppConfig(BaseModel):
    """Application configuration."""
    tables: Dict[str, TableConfig]
    monitoring: MonitoringConfig
    api: ApiConfig
    websocket: WebSocketConfig
    security: SecurityConfig
    environment: EnvironmentConfig

def load_config() -> AppConfig:
    """Load configuration for current environment."""
    stage = os.getenv('STAGE', 'development')
    config_path = Path(__file__).parent.parent.parent / 'config' / 'env.yaml'

    try:
        with open(config_path) as f:
            config_data = yaml.safe_load(f)

        # Get environment config
        env_config = config_data.get(stage, config_data['development'])
        
        # Merge with default config
        if 'default' in config_data:
            env_config = {**config_data['default'], **env_config}

        # Create full config
        full_config = {
            'tables': config_data['tables'],
            'monitoring': config_data['monitoring'],
            'api': config_data['api'],
            'websocket': config_data['websocket'],
            'security': config_data['security'],
            'environment': env_config
        }

        # Validate and return
        return AppConfig(**full_config)

    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        raise

def get_config() -> AppConfig:
    """Get configuration singleton."""
    if not hasattr(get_config, '_config'):
        get_config._config = load_config()
    return get_config._config

def get_table_name(table: str) -> str:
    """Get full table name for given table."""
    config = get_config()
    if table not in config.tables:
        raise ValueError(f"Unknown table: {table}")
    return config.tables[table].name

def get_dynamodb_endpoint() -> Optional[str]:
    """Get DynamoDB endpoint for current environment."""
    return get_config().environment.DYNAMODB_ENDPOINT

def is_local_environment() -> bool:
    """Check if running in local environment."""
    return get_config().environment.STAGE in ['development', 'test']