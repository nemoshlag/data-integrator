import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from typing import Dict, List, Optional, TypeVar, Type, Any
from aws_lambda_powertools import Logger
from datetime import datetime
import time

from .models import DynamoDBModel, ModelNotFoundError

logger = Logger()

# Type variable for DynamoDB models
T = TypeVar('T', bound=DynamoDBModel)

class DynamoDBClient:
    """Wrapper for DynamoDB operations."""
    
    def __init__(self, table_name: str):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)
        self.max_retries = 3
        self.base_delay = 0.1  # 100ms

    def _handle_error(self, operation: str, error: Exception) -> None:
        """Handle DynamoDB errors."""
        logger.error(f"DynamoDB {operation} error", 
                    extra={
                        "error": str(error),
                        "table": self.table.name
                    })
        raise error

    def get_item(self, model_class: Type[T], pk: str, sk: str) -> T:
        """Get item from DynamoDB."""
        try:
            response = self.table.get_item(Key={
                'PK': pk,
                'SK': sk
            })
            
            if 'Item' not in response:
                raise ModelNotFoundError(f"Item not found: {pk}/{sk}")
                
            return model_class.from_item(response['Item'])
        except ClientError as e:
            self._handle_error("get_item", e)

    def put_item(self, item: DynamoDBModel) -> None:
        """Put item into DynamoDB with retry logic."""
        retries = 0
        while True:
            try:
                self.table.put_item(Item=item.to_item())
                return
            except ClientError as e:
                if e.response['Error']['Code'] == 'ProvisionedThroughputExceededException':
                    if retries >= self.max_retries:
                        self._handle_error("put_item", e)
                    retries += 1
                    time.sleep(self.base_delay * (2 ** retries))
                else:
                    self._handle_error("put_item", e)

    def query_by_pk(self, model_class: Type[T], pk: str) -> List[T]:
        """Query items by partition key."""
        try:
            response = self.table.query(
                KeyConditionExpression=Key('PK').eq(pk)
            )
            return [model_class.from_item(item) for item in response.get('Items', [])]
        except ClientError as e:
            self._handle_error("query", e)

    def query_index(self, 
                   index_name: str,
                   key_condition: str,
                   values: Dict[str, Any],
                   model_class: Type[T]) -> List[T]:
        """Query items using a GSI."""
        try:
            response = self.table.query(
                IndexName=index_name,
                KeyConditionExpression=key_condition,
                ExpressionAttributeValues=values
            )
            return [model_class.from_item(item) for item in response.get('Items', [])]
        except ClientError as e:
            self._handle_error("query_index", e)

    def update_item(self, 
                   pk: str, 
                   sk: str, 
                   update_expression: str,
                   expression_values: Dict[str, Any]) -> None:
        """Update item in DynamoDB."""
        try:
            self.table.update_item(
                Key={
                    'PK': pk,
                    'SK': sk
                },
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
        except ClientError as e:
            self._handle_error("update_item", e)

    def batch_write(self, items: List[DynamoDBModel]) -> None:
        """Batch write items to DynamoDB with automatic retry and chunking."""
        chunk_size = 25  # DynamoDB limit
        
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i + chunk_size]
            retries = 0
            
            while True:
                try:
                    with self.table.batch_writer() as batch:
                        for item in chunk:
                            batch.put_item(Item=item.to_item())
                    break
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ProvisionedThroughputExceededException':
                        if retries >= self.max_retries:
                            self._handle_error("batch_write", e)
                        retries += 1
                        time.sleep(self.base_delay * (2 ** retries))
                    else:
                        self._handle_error("batch_write", e)

    def query_patients_without_tests(self, hours: int = 48) -> List[Dict]:
        """Query for patients without recent tests."""
        try:
            response = self.table.query(
                IndexName='MonitoringIndex',
                KeyConditionExpression='#status = :status AND hoursSinceTest >= :hours',
                ExpressionAttributeNames={
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':status': 'Active',
                    ':hours': hours
                }
            )
            return response.get('Items', [])
        except ClientError as e:
            self._handle_error("query_patients_without_tests", e)

# Initialize clients for each table
patients_table = DynamoDBClient(table_name=f"{process.env.PATIENTS_TABLE}")
admissions_table = DynamoDBClient(table_name=f"{process.env.ADMISSIONS_TABLE}")
tests_table = DynamoDBClient(table_name=f"{process.env.TESTS_TABLE}")