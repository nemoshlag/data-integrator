#!/usr/bin/env python3
"""End-to-end deployment test script."""
import argparse
import json
import requests
import websockets
import asyncio
import sys
from datetime import datetime
import boto3
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeploymentTester:
    def __init__(self, api_url: str, websocket_url: str, stage: str):
        self.api_url = api_url.rstrip('/')
        self.websocket_url = websocket_url
        self.stage = stage
        self.session = requests.Session()
        
        # Set up AWS clients
        self.s3 = boto3.client('s3')
        self.dynamodb = boto3.client('dynamodb')
    
    async def test_websocket(self) -> bool:
        """Test WebSocket connection and message handling."""
        try:
            async with websockets.connect(self.websocket_url) as websocket:
                # Wait for potential messages
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    logger.info("WebSocket connection successful")
                    return True
                except asyncio.TimeoutError:
                    # No message received, but connection worked
                    logger.info("WebSocket connection successful (no messages)")
                    return True
        except Exception as e:
            logger.error(f"WebSocket test failed: {str(e)}")
            return False

    def test_health_check(self) -> bool:
        """Test health check endpoint."""
        try:
            response = self.session.get(f"{self.api_url}/health")
            response.raise_for_status()
            
            data = response.json()
            if data['status'] != 'healthy':
                logger.error(f"Health check returned status: {data['status']}")
                return False
                
            logger.info("Health check successful")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False

    def test_monitoring_endpoint(self) -> bool:
        """Test patient monitoring endpoint."""
        try:
            response = self.session.get(
                f"{self.api_url}/patients/monitoring",
                params={'hours': 48}
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Found {data.get('totalCount', 0)} patients needing attention")
            return True
        except Exception as e:
            logger.error(f"Monitoring endpoint test failed: {str(e)}")
            return False

    def upload_test_data(self, bucket: str) -> bool:
        """Upload test data to S3."""
        try:
            # Create test patient data
            test_data = {
                'patient_id': 'TEST001',
                'first_name': 'Test',
                'last_name': 'Patient',
                'date_of_birth': '2000-01-01',
                'gender': 'M',
                'admission_id': 'ADM001',
                'admission_date': datetime.now().isoformat(),
                'ward': 'Test Ward',
                'bed_number': 'T101',
                'status': 'Active'
            }
            
            # Convert to CSV
            csv_data = ','.join(test_data.keys()) + '\n' + \
                      ','.join(str(v) for v in test_data.values())
            
            # Upload to S3
            self.s3.put_object(
                Bucket=bucket,
                Key=f'test/patient_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                Body=csv_data.encode('utf-8')
            )
            
            logger.info("Test data uploaded successfully")
            return True
        except Exception as e:
            logger.error(f"Test data upload failed: {str(e)}")
            return False

    async def run_all_tests(self, s3_bucket: str = None) -> bool:
        """Run all deployment tests."""
        results = {
            'health_check': self.test_health_check(),
            'monitoring': self.test_monitoring_endpoint(),
            'websocket': await self.test_websocket()
        }
        
        if s3_bucket:
            results['data_upload'] = self.upload_test_data(s3_bucket)
        
        # Print results
        logger.info("\nTest Results:")
        for test, result in results.items():
            logger.info(f"{test}: {'✅' if result else '❌'}")
        
        return all(results.values())

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Test deployment')
    parser.add_argument('--api-url', required=True, help='API Gateway URL')
    parser.add_argument('--websocket-url', required=True, help='WebSocket URL')
    parser.add_argument('--stage', default='dev', help='Deployment stage')
    parser.add_argument('--s3-bucket', help='S3 bucket for test data')
    return parser.parse_args()

async def main():
    """Main entry point."""
    args = parse_args()
    
    tester = DeploymentTester(
        api_url=args.api_url,
        websocket_url=args.websocket_url,
        stage=args.stage
    )
    
    success = await tester.run_all_tests(args.s3_bucket)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    asyncio.run(main())