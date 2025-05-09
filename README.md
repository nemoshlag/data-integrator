# Hospital Patient Monitoring System

A serverless application for monitoring hospital patients and tracking their test schedules. The system helps identify patients who haven't had tests in the last 48 hours and sends real-time alerts.

## Features

- Real-time patient monitoring
- Automatic processing of patient data from PMS and LIS systems
- DynamoDB-based data storage with efficient querying
- WebSocket-based real-time alerts
- REST API for data access

## Prerequisites

- Python 3.9+
- AWS Account
- Docker (for local development)
- Make (optional, for using Makefile commands)

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/yourusername/hospital-monitor.git
cd hospital-monitor
```

2. Set up development environment:
```bash
make dev-environment
source venv/bin/activate
```

3. Configure AWS credentials:
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=eu-west-1
```

4. Deploy to AWS:
```bash
make deploy STAGE=dev
```

## Development

### Local Testing

1. Start local DynamoDB:
```bash
make dynamodb-local
```

2. Run tests:
```bash
make test          # Run all tests
make test-unit     # Run unit tests only
make test-integration  # Run integration tests only
```

### Code Quality

1. Format code:
```bash
make format
```

2. Run linters:
```bash
make lint
```

## Project Structure

```
hospital-monitor/
├── src/
│   ├── functions/         # Lambda functions
│   │   ├── api/          # API handlers
│   │   ├── process_s3_upload/
│   │   └── monitor_patients/
│   ├── lib/              # Shared libraries
│   └── utils/            # Utilities
├── tests/
│   ├── unit/
│   └── integration/
└── sample_data/          # Sample data files
```

## API Documentation

### Get Patients Without Tests

```http
GET /patients/monitoring?hours=48&ward=Cardiology
```

Parameters:
- `hours` (optional): Hours since last test (default: 48)
- `ward` (optional): Filter by ward

Response:
```json
{
  "patients": [
    {
      "patientId": "P123",
      "firstName": "John",
      "lastName": "Doe",
      "ward": "Cardiology",
      "bedNumber": "C101",
      "lastTestDate": "2025-05-07T10:00:00",
      "hoursSinceTest": 48
    }
  ],
  "totalCount": 1,
  "timestamp": "2025-05-09T10:00:00Z"
}
```

## WebSocket Events

### Connect
```javascript
const ws = new WebSocket('wss://your-api.execute-api.region.amazonaws.com/dev');
```

### Event Types

1. Alert Message:
```json
{
  "type": "alert",
  "alertType": "noTest",
  "data": {
    "patientId": "P123",
    "message": "Patient hasn't had tests for 48 hours"
  }
}
```

## Deployment

### Development
```bash
make deploy STAGE=dev
```

### Production
```bash
make deploy STAGE=prod
```

### Validate Configuration
```bash
make validate
```

## Monitoring and Troubleshooting

### CloudWatch Logs
```bash
# View Lambda function logs
make watch-logs

# View specific function logs
serverless logs -f processS3Upload -t
serverless logs -f monitorPatients -t
```

### Metrics
- CloudWatch dashboard is available at: `AWS Console > CloudWatch > Dashboards > hospital-monitor-${stage}`
- Key metrics:
  - Patient monitoring latency
  - Data processing success rate
  - WebSocket connection count
  - DynamoDB read/write capacity

### Common Issues

1. DynamoDB Throughput
```bash
# Check table metrics
aws dynamodb describe-table --table-name hospital-monitor-dev-patients
```

2. Lambda Cold Starts
- Use Provisioned Concurrency for critical functions
- Monitor InitDuration in CloudWatch Logs

3. WebSocket Connections
- Check connection count in CloudWatch
- Monitor connection timeouts

## Contributing

1. Fork the repository
2. Create a feature branch
```bash
git checkout -b feature/your-feature-name
```

3. Make your changes and run tests
```bash
make lint
make test
```

4. Submit a pull request

### Coding Standards
- Use Black for code formatting
- Follow PEP 8 guidelines
- Add type hints to all functions
- Write unit tests for new features

## License

MIT License - see LICENSE file for details.

## Security

Report security issues to security@yourdomain.com

### Data Protection
- All patient data is encrypted at rest
- HTTPS/WSS for data in transit
- Access control through IAM roles
- Regular security audits

## Support

For support:
1. Check the documentation
2. Search existing issues
3. Open a new issue with:
   - System version
   - Error logs
   - Steps to reproduce

## Acknowledgments

- AWS Serverless team
- Hospital IT team
- Open source community