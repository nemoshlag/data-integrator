"""WebSocket utilities for real-time messaging."""
import json
import boto3
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
from aws_lambda_powertools.utilities.typing import LambdaContext

from .logging import get_logger
from .config import get_config
from .http import create_response, HttpError

logger = get_logger('websocket')
config = get_config()

class WebSocketMessage:
    """WebSocket message structure."""
    def __init__(
        self,
        type: str,
        data: Any,
        target: Optional[str] = None,
        timestamp: Optional[str] = None
    ):
        self.type = type
        self.data = data
        self.target = target
        self.timestamp = timestamp or datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            'type': self.type,
            'data': self.data,
            'target': self.target,
            'timestamp': self.timestamp
        }

    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps(self.to_dict())

class WebSocketConnection:
    """WebSocket connection manager."""
    def __init__(self, endpoint_url: str):
        self.endpoint_url = endpoint_url
        self.api_client = boto3.client('apigatewaymanagementapi', endpoint_url=endpoint_url)
        self.dynamodb = boto3.resource('dynamodb')
        self.connections_table = self.dynamodb.Table(f"{config.environment.STAGE}-websocket-connections")

    async def send_message(
        self,
        connection_id: str,
        message: WebSocketMessage
    ) -> bool:
        """Send message to a specific connection."""
        try:
            await self.api_client.post_to_connection(
                ConnectionId=connection_id,
                Data=message.to_json()
            )
            return True
        except self.api_client.exceptions.GoneException:
            logger.warning(f"Connection {connection_id} is gone, removing from database")
            await self.remove_connection(connection_id)
            return False
        except Exception as e:
            logger.error(f"Error sending message to {connection_id}: {str(e)}")
            return False

    async def broadcast_message(
        self,
        message: WebSocketMessage,
        exclude_connections: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """Broadcast message to all active connections."""
        stats = {
            'total': 0,
            'sent': 0,
            'failed': 0,
            'excluded': len(exclude_connections or [])
        }

        try:
            # Get all active connections
            response = self.connections_table.scan()
            connections = response.get('Items', [])
            stats['total'] = len(connections)

            # Send message to each connection
            for conn in connections:
                connection_id = conn['connectionId']
                if exclude_connections and connection_id in exclude_connections:
                    continue

                success = await self.send_message(connection_id, message)
                if success:
                    stats['sent'] += 1
                else:
                    stats['failed'] += 1

            return stats

        except Exception as e:
            logger.error(f"Error broadcasting message: {str(e)}")
            raise

    async def save_connection(
        self,
        connection_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Save new WebSocket connection."""
        try:
            item = {
                'connectionId': connection_id,
                'timestamp': datetime.utcnow().isoformat(),
                'ttl': int(datetime.utcnow().timestamp()) + config.websocket.connection_ttl
            }
            if metadata:
                item['metadata'] = metadata

            self.connections_table.put_item(Item=item)
            logger.info(f"Saved connection {connection_id}")

        except Exception as e:
            logger.error(f"Error saving connection {connection_id}: {str(e)}")
            raise

    async def remove_connection(self, connection_id: str) -> None:
        """Remove WebSocket connection."""
        try:
            self.connections_table.delete_item(
                Key={'connectionId': connection_id}
            )
            logger.info(f"Removed connection {connection_id}")

        except Exception as e:
            logger.error(f"Error removing connection {connection_id}: {str(e)}")
            raise

def handle_websocket_connect(event: Dict[str, Any], _: LambdaContext) -> Dict[str, Any]:
    """Handle WebSocket connect event."""
    connection_id = event['requestContext']['connectionId']
    
    try:
        websocket = WebSocketConnection(event['requestContext']['domainName'])
        asyncio.run(websocket.save_connection(connection_id))
        
        return create_response(200, {'message': 'Connected'})
    except Exception as e:
        logger.error(f"Error handling connection: {str(e)}")
        return create_response(500, {'message': 'Connection failed'})

def handle_websocket_disconnect(event: Dict[str, Any], _: LambdaContext) -> Dict[str, Any]:
    """Handle WebSocket disconnect event."""
    connection_id = event['requestContext']['connectionId']
    
    try:
        websocket = WebSocketConnection(event['requestContext']['domainName'])
        asyncio.run(websocket.remove_connection(connection_id))
        
        return create_response(200, {'message': 'Disconnected'})
    except Exception as e:
        logger.error(f"Error handling disconnection: {str(e)}")
        return create_response(500, {'message': 'Disconnection failed'})

async def send_alert(
    alert_type: str,
    alert_data: Dict[str, Any],
    websocket_api_url: str
) -> Dict[str, int]:
    """Send alert to all connected clients."""
    try:
        websocket = WebSocketConnection(websocket_api_url)
        message = WebSocketMessage(
            type='alert',
            data={
                'type': alert_type,
                'data': alert_data,
                'timestamp': datetime.utcnow().isoformat()
            }
        )
        
        stats = await websocket.broadcast_message(message)
        logger.info(f"Alert broadcast stats: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error sending alert: {str(e)}")
        raise