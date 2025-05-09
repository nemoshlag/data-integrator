"""Common constants used across the application."""

# CORS Headers
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Credentials': True,
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization'
}

# DynamoDB Index Names
MONITORING_INDEX = 'MonitoringIndex'
NAME_INDEX = 'NameIndex'
PATIENT_TEST_INDEX = 'PatientTestIndex'

# Status Constants
STATUS_ACTIVE = 'Active'
STATUS_DISCHARGED = 'Discharged'

# Time Constants
DEFAULT_MONITORING_HOURS = 48
BATCH_PROCESSING_SIZE = 100

# Response Messages
MSG_NO_PATIENTS = 'No patients need attention'
MSG_PROCESSING_COMPLETE = 'Processing complete'
MSG_ERROR_PROCESSING = 'Error processing request'

# Error Codes
ERR_INVALID_PARAMETERS = 'INVALID_PARAMETERS'
ERR_DATABASE_ERROR = 'DATABASE_ERROR'
ERR_PROCESSING_ERROR = 'PROCESSING_ERROR'

# Success Messages
MSG_SUCCESS = 'Success'
MSG_UPDATED = 'Updated successfully'