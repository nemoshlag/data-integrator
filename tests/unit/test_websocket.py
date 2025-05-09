"""Tests for WebSocket utilities."""
import pytest
from unittest.mock import MagicMock, patch
import json
from datetime import datetime
import boto3
from botocore.stub import Stubber

from src.utils.websocket import (
    WebSocketMessage,
    WebSocketConnection,
    handle_websocket_connect,
    handle_websocket_disconnect,
    send_alert
)

@pytest.fixture
def mock_api_client():
    """Mock API Gateway management client."""
    client = MagicMock()
    client.post_to_connection = MagicMock()
    client.exceptions.GoneException = Exception
    return client

@pytest.fixture
def mock_dynamodb_table():
    """Mock DynamoDB table."""
    table = MagicMock()
    table.scan = MagicMock(return_value={'Items': []})
    table.put_item = MagicMock()
    table.delete_item = MagicMock()
    return table

@pytest.fixture
def websocket_connection(mock_api_client, mock_dynamodb_table):
    """Create WebSocket connection with mocked dependencies."""
    conn = WebSocketConnection('https://test-api.example.com')
    conn.api_client = mock_api_client
    conn.connections_table = mock_dynamodb_table
    return conn

@pytest.fixture
def mock_event():
    """Create mock WebSocket event."""
    return {
        'requestContext': {
            'connectionId': 'test-connection-id',
            'domainName': 'test-api.example.com',
            'stage': 'dev'
        }
    }

def test_websocket_message():
    """Test WebSocket message creation and serialization."""
    data = {'test': 'data'}
    message = WebSocketMessage('test-type', data, 'test-target')
    
    # Test to_dict
    message_dict = message.to_dict()
    assert message_dict['type'] == 'test-type'
    assert message_dict['data'] == data
    assert message_dict['target'] == 'test-target'
    assert 'timestamp' in message_dict
    
    # Test to_json
    message_json = message.to_json()
    decoded = json.loads(message_json)
    assert decoded == message_dict

@pytest.mark.asyncio
async def test_send_message(websocket_connection):
    """Test sending message to a connection."""
    message = WebSocketMessage('test', {'data': 'test'})
    
    # Test successful send
    success = await websocket_connection.send_message('test-conn', message)
    assert success
    websocket_connection.api_client.post_to_connection.assert_called_once()
    
    # Test connection gone
    websocket_connection.api_client.post_to_connection.side_effect = \
        websocket_connection.api_client.exceptions.GoneException
    success = await websocket_connection.send_message('test-conn', message)
    assert not success
    websocket_connection.connections_table.delete_item.assert_called_once()

@pytest.mark.asyncio
async def test_broadcast_message(websocket_connection):
    """Test broadcasting messages to all connections."""
    # Setup mock connections
    connections = [
        {'connectionId': 'conn1'},
        {'connectionId': 'conn2'},
        {'connectionId': 'conn3'}
    ]
    websocket_connection.connections_table.scan.return_value = {'Items': connections}
    
    message = WebSocketMessage('broadcast', {'data': 'test'})
    
    # Test successful broadcast
    stats = await websocket_connection.broadcast_message(message)
    assert stats['total'] == 3
    assert stats['sent'] == 3
    assert stats['failed'] == 0
    
    # Test broadcast with exclusions
    stats = await websocket_connection.broadcast_message(
        message,
        exclude_connections=['conn1']
    )
    assert stats['excluded'] == 1
    assert stats['total'] == 3
    assert stats['sent'] == 2

@pytest.mark.asyncio
async def test_connection_management(websocket_connection):
    """Test connection management functions."""
    connection_id = 'test-conn'
    metadata = {'user': 'test'}
    
    # Test save connection
    await websocket_connection.save_connection(connection_id, metadata)
    websocket_connection.connections_table.put_item.assert_called_once()
    
    # Verify saved item contains required fields
    call_args = websocket_connection.connections_table.put_item.call_args
    saved_item = call_args[1]['Item']
    assert saved_item['connectionId'] == connection_id
    assert saved_item['metadata'] == metadata
    assert 'timestamp' in saved_item
    assert 'ttl' in saved_item
    
    # Test remove connection
    await websocket_connection.remove_connection(connection_id)
    websocket_connection.connections_table.delete_item.assert_called_with(
        Key={'connectionId': connection_id}
    )

def test_handle_websocket_connect(mock_event):
    """Test WebSocket connect handler."""
    response = handle_websocket_connect(mock_event, None)
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'Connected' in body['message']

def test_handle_websocket_disconnect(mock_event):
    """Test WebSocket disconnect handler."""
    response = handle_websocket_disconnect(mock_event, None)
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'Disconnected' in body['message']

@pytest.mark.asyncio
async def test_send_alert():
    """Test sending alerts through WebSocket."""
    with patch('src.utils.websocket.WebSocketConnection') as mock_conn:
        instance = mock_conn.return_value
        instance.broadcast_message.return_value = {
            'total': 5,
            'sent': 4,
            'failed': 1
        }
        
        stats = await send_alert(
            'test-alert',
            {'message': 'Test alert'},
            'wss://test-api.example.com'
        )
        
        assert stats['total'] == 5
        assert stats['sent'] == 4
        assert stats['failed'] == 1
        
        # Verify alert format
        call_args = instance.broadcast_message.call_args
        message = call_args[0][0]
        assert message.type == 'alert'
        assert message.data['type'] == 'test-alert'
        assert 'timestamp' in message.data

@pytest.mark.asyncio
async def test_error_handling(websocket_connection):
    """Test error handling in WebSocket operations."""
    # Test database error
    websocket_connection.connections_table.put_item.side_effect = Exception('DB Error')
    with pytest.raises(Exception):
        await websocket_connection.save_connection('test-conn')
    
    # Test API error
    websocket_connection.api_client.post_to_connection.side_effect = Exception('API Error')
    success = await websocket_connection.send_message('test-conn', WebSocketMessage('test', {}))
    assert not success