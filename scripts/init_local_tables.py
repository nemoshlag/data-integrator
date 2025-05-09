#!/usr/bin/env python3
"""Initialize local DynamoDB tables for development."""
import boto3
import time
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DynamoDB client for local instance
dynamodb = boto3.client('dynamodb', endpoint_url='http://localhost:8000')
dynamodb_resource = boto3.resource('dynamodb', endpoint_url='http://localhost:8000')

def create_table(table_name: str, definition: Dict[str, Any]) -> None:
    """Create a DynamoDB table if it doesn't exist."""
    try:
        table = dynamodb.create_table(**definition)
        logger.info(f"Creating table {table_name}...")
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=definition['TableName'])
        logger.info(f"Table {table_name} created successfully")
    except dynamodb.exceptions.ResourceInUseException:
        logger.info(f"Table {table_name} already exists")

def load_sample_data() -> None:
    """Load sample data into tables."""
    # Sample patient
    patient_table = dynamodb_resource.Table('dev-hospital-data-integrator-patients')
    patient_table.put_item(
        Item={
            'PK': 'PATIENT#P123',
            'SK': 'METADATA',
            'patient_id': 'P123',
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1980-01-01',
            'gender': 'M',
            'updated_at': datetime.now().isoformat()
        }
    )

    # Sample admission
    admission_table = dynamodb_resource.Table('dev-hospital-data-integrator-admissions')
    admission_table.put_item(
        Item={
            'PK': 'PATIENT#P123',
            'SK': 'ADMISSION#A456',
            'patient_id': 'P123',
            'admission_id': 'A456',
            'admission_date': datetime.now().isoformat(),
            'ward': 'Cardiology',
            'bed_number': 'C101',
            'status': 'Active',
            'last_test_date': (datetime.now() - timedelta(hours=49)).isoformat(),
            'hours_since_test': 49,
            'updated_at': datetime.now().isoformat()
        }
    )

    # Sample test
    test_table = dynamodb_resource.Table('dev-hospital-data-integrator-tests')
    test_table.put_item(
        Item={
            'PK': 'ADMISSION#A456',
            'SK': f'TEST#{datetime.now().isoformat()}#T789',
            'test_id': 'T789',
            'patient_id': 'P123',
            'admission_id': 'A456',
            'test_type': 'Blood Test',
            'test_date': datetime.now().isoformat(),
            'result': 'Normal',
            'status': 'Completed',
            'lab_location': 'Main Lab',
            'updated_at': datetime.now().isoformat()
        }
    )

    logger.info("Sample data loaded successfully")

def main():
    """Main function to initialize tables and load data."""
    try:
        # Create tables
        tables = {
            'patients': {
                'TableName': 'dev-hospital-data-integrator-patients',
                'AttributeDefinitions': [
                    {'AttributeName': 'PK', 'AttributeType': 'S'},
                    {'AttributeName': 'SK', 'AttributeType': 'S'}
                ],
                'KeySchema': [
                    {'AttributeName': 'PK', 'KeyType': 'HASH'},
                    {'AttributeName': 'SK', 'KeyType': 'RANGE'}
                ],
                'BillingMode': 'PAY_PER_REQUEST'
            },
            'admissions': {
                'TableName': 'dev-hospital-data-integrator-admissions',
                'AttributeDefinitions': [
                    {'AttributeName': 'PK', 'AttributeType': 'S'},
                    {'AttributeName': 'SK', 'AttributeType': 'S'},
                    {'AttributeName': 'status', 'AttributeType': 'S'},
                    {'AttributeName': 'hours_since_test', 'AttributeType': 'N'}
                ],
                'KeySchema': [
                    {'AttributeName': 'PK', 'KeyType': 'HASH'},
                    {'AttributeName': 'SK', 'KeyType': 'RANGE'}
                ],
                'GlobalSecondaryIndexes': [
                    {
                        'IndexName': 'MonitoringIndex',
                        'KeySchema': [
                            {'AttributeName': 'status', 'KeyType': 'HASH'},
                            {'AttributeName': 'hours_since_test', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'}
                    }
                ],
                'BillingMode': 'PAY_PER_REQUEST'
            },
            'tests': {
                'TableName': 'dev-hospital-data-integrator-tests',
                'AttributeDefinitions': [
                    {'AttributeName': 'PK', 'AttributeType': 'S'},
                    {'AttributeName': 'SK', 'AttributeType': 'S'}
                ],
                'KeySchema': [
                    {'AttributeName': 'PK', 'KeyType': 'HASH'},
                    {'AttributeName': 'SK', 'KeyType': 'RANGE'}
                ],
                'BillingMode': 'PAY_PER_REQUEST'
            }
        }

        for table_name, definition in tables.items():
            create_table(table_name, definition)

        # Load sample data
        load_sample_data()

        logger.info("Local DynamoDB initialization complete")

    except Exception as e:
        logger.error(f"Error initializing local DynamoDB: {str(e)}")
        raise

if __name__ == '__main__':
    main()