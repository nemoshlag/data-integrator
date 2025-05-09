# Serverless Framework Implementation

## Project Structure
```
hospital-monitoring/
├── serverless.yml
├── src/
│   ├── functions/
│   │   ├── processS3Upload/
│   │   │   ├── handler.ts
│   │   │   └── index.ts
│   │   ├── monitorPatients/
│   │   │   ├── handler.ts
│   │   │   └── index.ts
│   │   └── api/
│   │       ├── getPatientsWithoutTests.ts
│   │       └── getPatientDetails.ts
│   ├── lib/
│   │   ├── dynamodb.ts
│   │   └── websocket.ts
│   └── types/
│       └── index.ts
└── package.json
```

## Serverless Configuration

```yaml
service: hospital-monitoring

provider:
  name: aws
  runtime: nodejs16.x
  region: ${opt:region, 'eu-west-1'}
  environment:
    STAGE: ${opt:stage, 'dev'}
  iam:
    role:
      statements:
        - Effect: Allow
          Action:
            - dynamodb:Query
            - dynamodb:Scan
            - dynamodb:GetItem
            - dynamodb:PutItem
            - dynamodb:UpdateItem
            - dynamodb:DeleteItem
          Resource: 
            - !GetAtt PatientsTable.Arn
            - !GetAtt AdmissionsTable.Arn
            - !GetAtt TestsTable.Arn
        - Effect: Allow
          Action:
            - s3:GetObject
          Resource: "arn:aws:s3:::${self:custom.buckets.pms}/*"

custom:
  tableName: ${self:service}-${opt:stage, self:provider.stage}
  buckets:
    pms: external-take-home-test-wild-launch
  websocketApiName: ${self:service}-websocket-${opt:stage, self:provider.stage}

resources:
  Resources:
    PatientsTable:
      Type: AWS::DynamoDB::Table
      Properties:
        TableName: ${self:custom.tableName}-patients
        BillingMode: PAY_PER_REQUEST
        AttributeDefinitions:
          - AttributeName: PK
            AttributeType: S
          - AttributeName: SK
            AttributeType: S
          - AttributeName: lastName
            AttributeType: S
          - AttributeName: firstName
            AttributeType: S
        KeySchema:
          - AttributeName: PK
            KeyType: HASH
          - AttributeName: SK
            KeyType: RANGE
        GlobalSecondaryIndexes:
          - IndexName: NameIndex
            KeySchema:
              - AttributeName: lastName
                KeyType: HASH
              - AttributeName: firstName
                KeyType: RANGE
            Projection:
              ProjectionType: ALL

    AdmissionsTable:
      Type: AWS::DynamoDB::Table
      Properties:
        TableName: ${self:custom.tableName}-admissions
        BillingMode: PAY_PER_REQUEST
        AttributeDefinitions:
          - AttributeName: PK
            AttributeType: S
          - AttributeName: SK
            AttributeType: S
          - AttributeName: status
            AttributeType: S
          - AttributeName: hoursSinceTest
            AttributeType: N
          - AttributeName: ward
            AttributeType: S
        KeySchema:
          - AttributeName: PK
            KeyType: HASH
          - AttributeName: SK
            KeyType: RANGE
        GlobalSecondaryIndexes:
          - IndexName: MonitoringIndex
            KeySchema:
              - AttributeName: status
                KeyType: HASH
              - AttributeName: hoursSinceTest
                KeyType: RANGE
            Projection:
              ProjectionType: ALL
          - IndexName: WardIndex
            KeySchema:
              - AttributeName: ward
                KeyType: HASH
              - AttributeName: SK
                KeyType: RANGE
            Projection:
              ProjectionType: ALL

    TestsTable:
      Type: AWS::DynamoDB::Table
      Properties:
        TableName: ${self:custom.tableName}-tests
        BillingMode: PAY_PER_REQUEST
        AttributeDefinitions:
          - AttributeName: PK
            AttributeType: S
          - AttributeName: SK
            AttributeType: S
          - AttributeName: patientId
            AttributeType: S
          - AttributeName: testDate
            AttributeType: S
        KeySchema:
          - AttributeName: PK
            KeyType: HASH
          - AttributeName: SK
            KeyType: RANGE
        GlobalSecondaryIndexes:
          - IndexName: PatientTestIndex
            KeySchema:
              - AttributeName: patientId
                KeyType: HASH
              - AttributeName: testDate
                KeyType: RANGE
            Projection:
              ProjectionType: ALL

functions:
  processS3Upload:
    handler: src/functions/processS3Upload/handler.default
    events:
      - s3:
          bucket: ${self:custom.buckets.pms}
          event: s3:ObjectCreated:*
          existing: true
    environment:
      PATIENTS_TABLE: ${self:custom.tableName}-patients
      ADMISSIONS_TABLE: ${self:custom.tableName}-admissions
      TESTS_TABLE: ${self:custom.tableName}-tests

  monitorPatients:
    handler: src/functions/monitorPatients/handler.default
    events:
      - schedule: rate(1 minute)
    environment:
      ADMISSIONS_TABLE: ${self:custom.tableName}-admissions
      WEBSOCKET_API_URL: !GetAtt WebsocketApi.ApiEndpoint

  getPatientsWithoutTests:
    handler: src/functions/api/getPatientsWithoutTests.default
    events:
      - http:
          path: /patients/monitoring
          method: get
          cors: true
    environment:
      ADMISSIONS_TABLE: ${self:custom.tableName}-admissions

  # WebSocket API
  websocketConnect:
    handler: src/functions/websocket/connect.default
    events:
      - websocket:
          route: $connect
  
  websocketDisconnect:
    handler: src/functions/websocket/disconnect.default
    events:
      - websocket:
          route: $disconnect

  websocketDefault:
    handler: src/functions/websocket/default.default
    events:
      - websocket:
          route: $default

plugins:
  - serverless-plugin-typescript
  - serverless-offline
  - serverless-dynamodb-local

package:
  individually: true
```

## Lambda Function Examples

### 1. Process S3 Upload
```typescript
// src/functions/processS3Upload/handler.ts
import { S3Handler } from 'aws-lambda';
import { DynamoDB } from 'aws-sdk';
import { processCSVFile } from './processFile';

const dynamodb = new DynamoDB.DocumentClient();

export const handler: S3Handler = async (event) => {
  try {
    const bucket = event.Records[0].s3.bucket.name;
    const key = event.Records[0].s3.object.key;
    
    // Process file and extract data
    const data = await processCSVFile(bucket, key);
    
    // Update DynamoDB
    await Promise.all(data.map(async (item) => {
      await dynamodb.put({
        TableName: process.env.PATIENTS_TABLE!,
        Item: {
          PK: `PATIENT#${item.patientId}`,
          SK: 'METADATA',
          firstName: item.firstName,
          lastName: item.lastName,
          // ... other fields
        }
      }).promise();
      
      // Update admission if present
      if (item.admissionId) {
        await dynamodb.put({
          TableName: process.env.ADMISSIONS_TABLE!,
          Item: {
            PK: `PATIENT#${item.patientId}`,
            SK: `ADMISSION#${item.admissionId}`,
            // ... admission fields
          }
        }).promise();
      }
    }));
    
  } catch (error) {
    console.error('Error processing S3 upload:', error);
    throw error;
  }
};
```

### 2. Monitor Patients
```typescript
// src/functions/monitorPatients/handler.ts
import { ScheduledHandler } from 'aws-lambda';
import { DynamoDB, ApiGatewayManagementApi } from 'aws-sdk';

const dynamodb = new DynamoDB.DocumentClient();

export const handler: ScheduledHandler = async () => {
  try {
    // Query patients needing attention
    const result = await dynamodb.query({
      TableName: process.env.ADMISSIONS_TABLE!,
      IndexName: 'MonitoringIndex',
      KeyConditionExpression: 
        'status = :status AND hoursSinceTest >= :hours',
      ExpressionAttributeValues: {
        ':status': 'Active',
        ':hours': 48
      }
    }).promise();

    // If patients found, send alerts
    if (result.Items && result.Items.length > 0) {
      // Send WebSocket notifications
      const api = new ApiGatewayManagementApi({
        endpoint: process.env.WEBSOCKET_API_URL
      });

      // Send to all connected clients
      // Implementation details for managing connections omitted
    }
  } catch (error) {
    console.error('Error monitoring patients:', error);
    throw error;
  }
};
```

This Serverless Framework configuration provides:
1. DynamoDB table definitions with appropriate indexes
2. Lambda functions for processing data and monitoring
3. WebSocket API for real-time updates
4. HTTP API for querying patient data
5. Scheduled monitoring function

Benefits:
1. Simple deployment with `serverless deploy`
2. Local development with `serverless offline`
3. Easy configuration management
4. Automatic IAM role management

Next steps would be implementing the detailed Lambda function logic and setting up the frontend application.