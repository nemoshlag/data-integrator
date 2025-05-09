"""Lambda handler for getting patients without tests."""
from typing import Dict, Any, List, Optional
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from datetime import datetime

from ...lib.dynamodb import admissions_table, patients_table
from ...lib.models import Admission, Patient
from ...utils.api import create_response, create_error_response, parse_query_params, handle_options_request
from ...utils.constants import (
    DEFAULT_MONITORING_HOURS,
    ERR_DATABASE_ERROR,
    MSG_NO_PATIENTS,
    STATUS_ACTIVE,
    MONITORING_INDEX
)

logger = Logger()

def get_patient_details(patient_id: str) -> Optional[Dict[str, Any]]:
    """Get patient details from DynamoDB."""
    try:
        patient = patients_table.get_item(
            model_class=Patient,
            pk=f"PATIENT#{patient_id}",
            sk="METADATA"
        )
        
        if not patient:
            return None

        return {
            'patientId': patient.patient_id,
            'firstName': patient.first_name,
            'lastName': patient.last_name,
            'dateOfBirth': patient.date_of_birth,
            'gender': patient.gender
        }
    except Exception as e:
        logger.error(f"Error getting patient details: {str(e)}")
        return None

def get_patients_without_tests(hours: int = DEFAULT_MONITORING_HOURS, ward: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get patients who haven't had tests in the specified hours."""
    try:
        # Query admissions by monitoring index
        admissions = admissions_table.query_index(
            index_name=MONITORING_INDEX,
            key_condition='#status = :status AND hoursSinceTest >= :hours',
            values={
                ':status': STATUS_ACTIVE,
                ':hours': hours
            },
            model_class=Admission
        )
        
        # Filter by ward if specified
        if ward:
            admissions = [a for a in admissions if a.ward.lower() == ward.lower()]
        
        # Get patient details and combine with admission data
        results = []
        for admission in admissions:
            patient_details = get_patient_details(admission.patient_id)
            if patient_details:
                results.append({
                    **patient_details,
                    'admissionId': admission.admission_id,
                    'admissionDate': admission.admission_date,
                    'ward': admission.ward,
                    'bedNumber': admission.bed_number,
                    'lastTestDate': admission.last_test_date,
                    'hoursSinceTest': admission.hours_since_test,
                    'status': admission.status
                })
        
        # Sort by hours since test (descending)
        results.sort(key=lambda x: x['hoursSinceTest'] or float('inf'), reverse=True)
        
        return results
    
    except Exception as e:
        logger.error(f"Error getting patients without tests: {str(e)}")
        raise

@logger.inject_lambda_context
def handle(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Handle API Gateway request for patient monitoring data."""
    # Handle OPTIONS request for CORS
    if event.get('httpMethod') == 'OPTIONS':
        return handle_options_request()

    try:
        # Parse query parameters
        params = parse_query_params(event, {
            'hours': DEFAULT_MONITORING_HOURS,
            'ward': None
        })
        
        # Get patients without tests
        patients = get_patients_without_tests(
            hours=params['hours'],
            ward=params['ward']
        )
        
        if not patients:
            return create_response(
                status_code=200,
                body={
                    'message': MSG_NO_PATIENTS,
                    'patients': [],
                    'totalCount': 0,
                    'filters': params
                }
            )
        
        return create_response(
            status_code=200,
            body={
                'patients': patients,
                'totalCount': len(patients),
                'filters': params
            }
        )
        
    except Exception as e:
        logger.error(f"Error in handler: {str(e)}")
        return create_error_response(
            error_message=str(e),
            error_code=ERR_DATABASE_ERROR
        )