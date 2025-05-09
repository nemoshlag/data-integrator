"""Test configuration and fixtures."""
import pytest
import boto3
import os
from typing import Dict, Generator
from contextlib import contextmanager

from .utils import TEST_ENV, TABLE_DEFINITIONS, SAMPLE_PATIENT, SAMPLE_ADMISSION, SAMPLE_TEST

@pytest.fixture(scope='session', autouse=True)
def aws_credentials():
    """Configure AWS credentials for tests."""
    os.environ.update(TEST_ENV)

@pytest.fixture(scope='session')
def dynamodb_client():
    """Get DynamoDB client."""
    return boto3.client('dynamodb', endpoint_url='http://localhost:8000')

@pytest.fixture(scope='session')
def dynamodb_resource():
    """Get DynamoDB resource."""
    return boto3.resource('dynamodb', endpoint_url='http://localhost:8000')

@contextmanager
def create_table(dynamodb_resource, table_definition: Dict) -> Generator:
    """Create and delete a DynamoDB table."""
    table = dynamodb_resource.create_table(**table_definition)
    table.wait_until_exists()
    try:
        yield table
    finally:
        table.delete()
        table.wait_until_not_exists()

@pytest.fixture(scope='function')
def test_tables(dynamodb_resource):
    """Create test tables for each test."""
    tables = {}
    
    try:
        # Create all tables
        for table_name, definition in TABLE_DEFINITIONS.items():
            with create_table(dynamodb_resource, definition) as table:
                tables[table_name] = table
                
                # Load sample data
                if table_name == 'patients':
                    table.put_item(Item=SAMPLE_PATIENT)
                elif table_name == 'admissions':
                    table.put_item(Item=SAMPLE_ADMISSION)
                elif table_name == 'tests':
                    table.put_item(Item=SAMPLE_TEST)
        
        yield tables
        
    finally:
        # Cleanup is handled by the context manager
        pass

@pytest.fixture(scope='function')
def patient_without_tests(test_tables):
    """Create a test patient without recent tests."""
    patient_data = {
        'PK': 'PATIENT#P999',
        'SK': 'METADATA',
        'patient_id': 'P999',
        'first_name': 'Jane',
        'last_name': 'Smith',
        'date_of_birth': '1985-05-05',
        'gender': 'F'
    }
    
    admission_data = {
        'PK': 'PATIENT#P999',
        'SK': 'ADMISSION#A999',
        'patient_id': 'P999',
        'admission_id': 'A999',
        'admission_date': '2025-05-01T10:00:00',
        'ward': 'Neurology',
        'bed_number': 'N101',
        'status': 'Active',
        'last_test_date': None,
        'hours_since_test': 999  # High value to ensure it appears in monitoring
    }
    
    test_tables['patients'].put_item(Item=patient_data)
    test_tables['admissions'].put_item(Item=admission_data)
    
    return {
        'patient': patient_data,
        'admission': admission_data
    }

@pytest.fixture(scope='function')
def sample_s3_event():
    """Create a sample S3 event."""
    return {
        'Records': [{
            's3': {
                'bucket': {
                    'name': 'test-bucket'
                },
                'object': {
                    'key': 'test-file.csv'
                }
            }
        }]
    }