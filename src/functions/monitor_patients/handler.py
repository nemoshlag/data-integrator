import json
import boto3
from datetime import datetime
from typing import Dict, Any, List
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import os

from ...lib.models import Admission
from ...lib.dynamodb import admissions_table

logger = Logger()
api_client = boto3.client('apigatewaymanagementapi', 
                         endpoint_url=os.environ['WEBSOCKET_API_URL'])

class WebSocketManager:
    def __init__(self):
        self.ddb = boto3.resource('dynamodb')
        self.connections_table = self.ddb.Table(f"{os.environ['STAGE']}-websocket-connections")

    def get_connections(self) -> List[str]:
        """Get all active WebSocket connections."""
        try:
            response = self.connections_table.scan()
            return [item['connectionId'] for item in response.get('Items', [])]
        except Exception as e:
            logger.error(f"Error getting connections: {str(e)}")
            return []

    async def broadcast_message(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all connected clients."""
        connections = self.get_connections()
        
        for connection_id in connections:
            try:
                await api_client.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps(message)
                )
            except Exception as e:
                if 'GoneException' in str(e):
                    # Connection is no longer valid, delete it
                    try:
                        self.connections_table.delete_item(
                            Key={'connectionId': connection_id}
                        )
                    except Exception as del_err:
                        logger.error(f"Error deleting connection: {str(del_err)}")
                else:
                    logger.error(f"Error sending message: {str(e)}")

def get_patients_needing_attention() -> List[Dict[str, Any]]:
    """Get patients who need attention (no tests for >48 hours)."""
    try:
        response = admissions_table.query_index(
            index_name='MonitoringIndex',
            key_condition='#status = :status AND hoursSinceTest >= :hours',
            values={
                ':status': 'Active',
                ':hours': 48
            },
            model_class=Admission
        )
        
        # Transform to response format
        patients = []
        for admission in response:
            patients.append({
                'patientId': admission.patient_id,
                'admissionId': admission.admission_id,
                'ward': admission.ward,
                'bedNumber': admission.bed_number,
                'lastTestDate': admission.last_test_date,
                'hoursSinceTest': admission.hours_since_test
            })
        
        return patients
    
    except Exception as e:
        logger.error(f"Error querying patients: {str(e)}")
        raise

def create_alert_message(patient: Dict[str, Any]) -> Dict[str, Any]:
    """Create alert message for WebSocket broadcast."""
    return {
        'type': 'alert',
        'alertType': 'noTest',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'patientId': patient['patientId'],
            'admissionId': patient['admissionId'],
            'ward': patient['ward'],
            'bedNumber': patient['bedNumber'],
            'lastTestDate': patient['lastTestDate'],
            'hoursSinceTest': patient['hoursSinceTest'],
            'message': f"Patient {patient['patientId']} has not had tests for {patient['hoursSinceTest']} hours"
        }
    }

@logger.inject_lambda_context
async def handle(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Monitor patients and send alerts for those needing attention."""
    try:
        # Get patients needing attention
        patients = get_patients_needing_attention()
        
        if not patients:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'No patients need attention',
                    'timestamp': datetime.now().isoformat()
                })
            }
        
        # Initialize WebSocket manager
        ws_manager = WebSocketManager()
        
        # Send alerts for each patient
        for patient in patients:
            alert = create_alert_message(patient)
            await ws_manager.broadcast_message(alert)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Monitoring complete',
                'patientsAlerted': len(patients),
                'timestamp': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Error in monitoring: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
        }