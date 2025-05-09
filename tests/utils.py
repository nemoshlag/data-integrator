"""Test utilities and configurations."""
from typing import Dict, Any

# Test environment variables
TEST_ENV = {
    'AWS_ACCESS_KEY_ID': 'test',
    'AWS_SECRET_ACCESS_KEY': 'test',
    'AWS_DEFAULT_REGION': 'local',
    'STAGE': 'test',
    'PATIENTS_TABLE': 'test-patients',
    'ADMISSIONS_TABLE': 'test-admissions',
    'TESTS_TABLE': 'test-tests'
}

# DynamoDB table definitions
TABLE_DEFINITIONS = {
    'patients': {
        'TableName': TEST_ENV['PATIENTS_TABLE'],
        'KeySchema': [
            {'AttributeName': 'PK', 'KeyType': 'HASH'},
            {'AttributeName': 'SK', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'PK', 'AttributeType': 'S'},
            {'AttributeName': 'SK', 'AttributeType': 'S'}
        ],
        'BillingMode': 'PAY_PER_REQUEST'
    },
    'admissions': {
        'TableName': TEST_ENV['ADMISSIONS_TABLE'],
        'KeySchema': [
            {'AttributeName': 'PK', 'KeyType': 'HASH'},
            {'AttributeName': 'SK', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'PK', 'AttributeType': 'S'},
            {'AttributeName': 'SK', 'AttributeType': 'S'},
            {'AttributeName': 'status', 'AttributeType': 'S'},
            {'AttributeName': 'hoursSinceTest', 'AttributeType': 'N'}
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'MonitoringIndex',
                'KeySchema': [
                    {'AttributeName': 'status', 'KeyType': 'HASH'},
                    {'AttributeName': 'hoursSinceTest', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ],
        'BillingMode': 'PAY_PER_REQUEST'
    },
    'tests': {
        'TableName': TEST_ENV['TESTS_TABLE'],
        'KeySchema': [
            {'AttributeName': 'PK', 'KeyType': 'HASH'},
            {'AttributeName': 'SK', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'PK', 'AttributeType': 'S'},
            {'AttributeName': 'SK', 'AttributeType': 'S'}
        ],
        'BillingMode': 'PAY_PER_REQUEST'
    }
}

# Sample test data
SAMPLE_PATIENT = {
    'PK': 'PATIENT#P123',
    'SK': 'METADATA',
    'patient_id': 'P123',
    'first_name': 'John',
    'last_name': 'Doe',
    'date_of_birth': '1980-01-01',
    'gender': 'M'
}

SAMPLE_ADMISSION = {
    'PK': 'PATIENT#P123',
    'SK': 'ADMISSION#A456',
    'patient_id': 'P123',
    'admission_id': 'A456',
    'admission_date': '2025-05-01T10:00:00',
    'ward': 'Cardiology',
    'bed_number': 'C101',
    'status': 'Active',
    'last_test_date': '2025-05-07T10:00:00',
    'hours_since_test': 48
}

SAMPLE_TEST = {
    'PK': 'ADMISSION#A456',
    'SK': 'TEST#2025-05-07T10:00:00#T789',
    'test_id': 'T789',
    'patient_id': 'P123',
    'admission_id': 'A456',
    'test_type': 'Blood Test',
    'test_date': '2025-05-07T10:00:00',
    'result': 'Normal',
    'status': 'Completed',
    'lab_location': 'Main Lab'
}

def create_test_event(path: str = '/patients/monitoring', 
                     method: str = 'GET',
                     query_params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create a test API Gateway event."""
    return {
        'path': path,
        'httpMethod': method,
        'queryStringParameters': query_params or {},
        'headers': {
            'Content-Type': 'application/json'
        },
        'requestContext': {
            'stage': 'test'
        }
    }