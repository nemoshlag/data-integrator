"""Health check endpoint for the API."""
import json
from typing import Dict, Any
from datetime import datetime
import boto3
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from ...lib.dynamodb import patients_table, admissions_table, tests_table
from ...utils.api import create_response, create_error_response
from ...utils.constants import MSG_SUCCESS, ERR_DATABASE_ERROR

logger = Logger()

def check_dynamodb_tables() -> Dict[str, bool]:
    """Check if DynamoDB tables are accessible."""
    tables = {
        'patients': patients_table,
        'admissions': admissions_table,
        'tests': tests_table
    }
    
    results = {}
    for name, table in tables.items():
        try:
            # Try to scan with limit 1 to check access
            table.table.scan(Limit=1)
            results[name] = True
        except Exception as e:
            logger.error(f"Error checking {name} table: {str(e)}")
            results[name] = False
    
    return results

@logger.inject_lambda_context
def handle(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Handle health check request."""
    try:
        # Check DynamoDB connectivity
        db_status = check_dynamodb_tables()
        all_tables_ok = all(db_status.values())
        
        # Basic health metrics
        health_data = {
            'status': 'healthy' if all_tables_ok else 'degraded',
            'timestamp': datetime.now().isoformat(),
            'version': '0.1.0',
            'services': {
                'dynamodb': {
                    'status': 'healthy' if all_tables_ok else 'degraded',
                    'tables': db_status
                }
            }
        }
        
        status_code = 200 if all_tables_ok else 503
        
        return create_response(
            status_code=status_code,
            body=health_data
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return create_error_response(
            error_message="Health check failed",
            error_code=ERR_DATABASE_ERROR,
            status_code=500
        )