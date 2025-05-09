import json
import boto3
from typing import Dict, Any
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import os

logger = Logger()
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(f"{os.environ['STAGE']}-websocket-connections")

def save_connection(connection_id: str) -> None:
    """Save WebSocket connection ID to DynamoDB."""
    try:
        table.put_item(
            Item={
                'connectionId': connection_id,
                'timestamp': os.environ['_X_AMZN_TRACE_ID']
            }
        )
    except Exception as e:
        logger.error(f"Error saving connection: {str(e)}")
        raise

def delete_connection(connection_id: str) -> None:
    """Delete WebSocket connection ID from DynamoDB."""
    try:
        table.delete_item(
            Key={
                'connectionId': connection_id
            }
        )
    except Exception as e:
        logger.error(f"Error deleting connection: {str(e)}")
        raise

@logger.inject_lambda_context
def connect(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Handle WebSocket connect event."""
    try:
        connection_id = event['requestContext']['connectionId']
        save_connection(connection_id)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Connected successfully',
                'connectionId': connection_id
            })
        }
    except Exception as e:
        logger.error(f"Error in connect handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }

@logger.inject_lambda_context
def disconnect(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Handle WebSocket disconnect event."""
    try:
        connection_id = event['requestContext']['connectionId']
        delete_connection(connection_id)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Disconnected successfully',
                'connectionId': connection_id
            })
        }
    except Exception as e:
        logger.error(f"Error in disconnect handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }

@logger.inject_lambda_context
def default(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Handle WebSocket default message event."""
    try:
        connection_id = event['requestContext']['connectionId']
        
        # Parse message body
        body = json.loads(event.get('body', '{}'))
        message_type = body.get('type')
        
        response_message = {
            'type': 'response',
            'originalType': message_type,
            'message': 'Message received'
        }
        
        # Send response back to client
        api_client = boto3.client('apigatewaymanagementapi', 
                                endpoint_url=os.environ['WEBSOCKET_API_URL'])
        
        api_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(response_message)
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Message handled successfully',
                'connectionId': connection_id
            })
        }
    except Exception as e:
        logger.error(f"Error in default handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }

# Helper function for broadcasting messages
async def broadcast_message(message: Dict[str, Any]) -> None:
    """Broadcast message to all connected clients."""
    try:
        # Get all connections
        response = table.scan()
        connections = response.get('Items', [])
        
        # Initialize API client
        api_client = boto3.client('apigatewaymanagementapi', 
                                endpoint_url=os.environ['WEBSOCKET_API_URL'])
        
        # Send message to each connection
        for connection in connections:
            try:
                await api_client.post_to_connection(
                    ConnectionId=connection['connectionId'],
                    Data=json.dumps(message)
                )
            except Exception as e:
                if 'GoneException' in str(e):
                    # Connection is no longer valid, delete it
                    delete_connection(connection['connectionId'])
                else:
                    logger.error(f"Error sending message: {str(e)}")
                    
    except Exception as e:
        logger.error(f"Error broadcasting message: {str(e)}")
        raise