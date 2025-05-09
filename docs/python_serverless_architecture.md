# Python Serverless Architecture

## Project Structure
```
hospital-monitoring/
├── serverless.yml
├── requirements.txt
├── src/
│   ├── functions/
│   │   ├── process_s3_upload/
│   │   │   ├── handler.py
│   │   │   └── utils.py
│   │   ├── monitor_patients/
│   │   │   ├── handler.py
│   │   │   └── monitoring.py
│   │   └── api/
│   │       ├── get_patients.py
│   │       └── websocket.py
│   ├── lib/
│   │   ├── dynamodb.py
│   │   └── models.py
│   └── utils/
│       ├── constants.py
│       └── validators.py
└── tests/
    ├── unit/
    └── integration/
```

## Dependencies
```python
# requirements.txt
boto3>=1.26.137
pydantic>=1.10.7
python-dateutil>=2.8.2
pandas>=2.0.1
pytest>=7.3.1
aws-lambda-powertools>=2.15.0
websockets>=11.0.3
```

## DynamoDB Models

```python
# src/lib/models.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Patient:
    patient_id: str
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str
    updated_at: str

    @property
    def pk(self) -> str:
        return f"PATIENT#{self.patient_id}"

    @property
    def sk(self) -> str:
        return "METADATA"

@dataclass
class Admission:
    patient_id: str
    admission_id: str
    admission_date: datetime
    ward: str
    bed_number: str
    status: str
    last_test_date: Optional[datetime] = None
    hours_since_test: Optional[int] = None
    updated_at: datetime = datetime.now()

    @property
    def pk(self) -> str:
        return f"PATIENT#{self.patient_id}"

    @property
    def sk(self) -> str:
        return f"ADMISSION#{self.admission_id}"

@dataclass
class LabTest:
    test_id: str
    patient_id: str
    admission_id: str
    test_type: str
    test_date: datetime
    result: str
    status: str
    lab_location: str
    updated_at: datetime = datetime.now()

    @property
    def pk(self) -> str:
        return f"ADMISSION#{self.admission_id}"

    @property
    def sk(self) -> str:
        return f"TEST#{self.test_date.isoformat()}#{self.test_id}"
```

## Serverless Configuration

```yaml
# serverless.yml
service: hospital-monitoring

provider:
  name: aws
  runtime: python3.9
  region: eu-west-1
  environment:
    STAGE: ${opt:stage, 'dev'}
  iam:
    role:
      statements:
        - Effect: Allow
          Action:
            - dynamodb:*
          Resource: 
            - "arn:aws:dynamodb:${aws:region}:${aws:accountId}:table/${self:custom.tableName}-*"
        - Effect: Allow
          Action:
            - s3:GetObject
          Resource: "arn:aws:s3:::${self:custom.buckets.pms}/*"

package:
  individually: true
  patterns:
    - '!node_modules/**'
    - '!venv/**'
    - '!__pycache__/**'
    - '!.pytest_cache/**'

functions:
  processS3Upload:
    handler: src/functions/process_s3_upload/handler.handle
    events:
      - s3:
          bucket: ${self:custom.buckets.pms}
          event: s3:ObjectCreated:*
          existing: true

  monitorPatients:
    handler: src/functions/monitor_patients/handler.handle
    events:
      - schedule: rate(1 minute)

  getPatientsWithoutTests:
    handler: src/functions/api/get_patients.handle
    events:
      - http:
          path: /patients/monitoring
          method: get
          cors: true

plugins:
  - serverless-python-requirements
  - serverless-offline
```

## Lambda Function Examples

### Process S3 Upload
```python
# src/functions/process_s3_upload/handler.py
from typing import Dict, Any
import boto3
import pandas as pd
from datetime import datetime
from aws_lambda_powertools import Logger
from lib.models import Patient, Admission

logger = Logger()
dynamodb = boto3.resource('dynamodb')

@logger.inject_lambda_context
def handle(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        # Get S3 object details
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        
        # Read CSV data
        s3 = boto3.client('s3')
        obj = s3.get_object(Bucket=bucket, Key=key)
        df = pd.read_csv(obj['Body'])
        
        # Process each row
        for _, row in df.iterrows():
            # Create Patient record
            patient = Patient(
                patient_id=row['patient_id'],
                first_name=row['first_name'],
                last_name=row['last_name'],
                date_of_birth=row['date_of_birth'],
                gender=row['gender'],
                updated_at=datetime.now().isoformat()
            )
            
            # Create Admission record if present
            if 'admission_id' in row:
                admission = Admission(
                    patient_id=row['patient_id'],
                    admission_id=row['admission_id'],
                    admission_date=datetime.fromisoformat(row['admission_date']),
                    ward=row['ward'],
                    bed_number=row['bed_number'],
                    status=row['status']
                )
                
                # Save admission
                save_admission(admission)
            
            # Save patient
            save_patient(patient)
            
        return {'statusCode': 200, 'body': 'Processing complete'}
        
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise
```

### Monitor Patients
```python
# src/functions/monitor_patients/handler.py
from typing import Dict, Any
import boto3
from datetime import datetime, timedelta
from aws_lambda_powertools import Logger
from lib.models import Admission

logger = Logger()
dynamodb = boto3.resource('dynamodb')

@logger.inject_lambda_context
def handle(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        # Query for active admissions
        table = dynamodb.Table('admissions')
        response = table.query(
            IndexName='MonitoringIndex',
            KeyConditionExpression='#status = :status AND hoursSinceTest >= :hours',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':status': 'Active',
                ':hours': 48
            }
        )
        
        # Process results and send alerts
        for item in response['Items']:
            send_alert(item)
            
        return {'statusCode': 200, 'body': 'Monitoring complete'}
        
    except Exception as e:
        logger.error(f"Error monitoring patients: {str(e)}")
        raise
```

## Development Process

1. Local Development
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run local DynamoDB
serverless dynamodb install
serverless dynamodb start

# Run API locally
serverless offline
```

2. Testing
```bash
# Unit tests
pytest tests/unit

# Integration tests
pytest tests/integration
```

3. Deployment
```bash
# Deploy to development
serverless deploy --stage dev

# Deploy to production
serverless deploy --stage prod
```

## Performance Optimization

1. DynamoDB Access Patterns
- Use single-table design
- Optimize GSIs for monitoring queries
- Implement pagination for large result sets

2. Lambda Functions
- Keep functions focused and small
- Use connection pooling
- Implement caching where appropriate

3. Real-time Updates
- Use WebSocket API for instant notifications
- Implement connection management
- Handle reconnection scenarios

This architecture provides a scalable, maintainable solution using Python and serverless technologies, optimized for the hospital monitoring requirements.