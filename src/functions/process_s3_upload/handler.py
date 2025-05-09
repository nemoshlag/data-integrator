import json
import boto3
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from io import StringIO

from ...lib.models import Patient, Admission, LabTest
from ...lib.dynamodb import patients_table, admissions_table, tests_table

logger = Logger()
s3_client = boto3.client('s3')

def process_pms_record(record: Dict[str, Any]) -> Tuple[Patient, Optional[Admission]]:
    """Process a PMS record and return Patient and Admission instances."""
    # Create Patient instance
    patient = Patient(
        patient_id=record['patient_id'],
        first_name=record['first_name'],
        last_name=record['last_name'],
        date_of_birth=record['date_of_birth'],
        gender=record['gender'],
        updated_at=datetime.now().isoformat()
    )
    
    # Create Admission instance if admission data exists
    admission = None
    if 'admission_id' in record:
        admission = Admission(
            patient_id=record['patient_id'],
            admission_id=record['admission_id'],
            admission_date=record['admission_date'],
            ward=record['ward'],
            bed_number=record['bed_number'],
            status=record['status'],
            updated_at=datetime.now().isoformat()
        )
    
    return patient, admission

def process_lis_record(record: Dict[str, Any]) -> LabTest:
    """Process a LIS record and return LabTest instance."""
    test = LabTest(
        test_id=record['test_id'],
        patient_id=record['patient_id'],
        admission_id=record['admission_id'],
        test_type=record['test_type'],
        test_date=record['test_date'],
        result=record['result'],
        status=record['status'],
        lab_location=record['lab_location'],
        updated_at=datetime.now().isoformat()
    )
    
    return test

def update_admission_test_date(admission_id: str, test_date: str) -> None:
    """Update admission's last test date and hours since test."""
    hours_since_test = 0  # New test, so 0 hours
    
    admissions_table.update_item(
        pk=f"PATIENT#{admission_id.split('#')[0]}",  # Extract patient_id
        sk=f"ADMISSION#{admission_id}",
        update_expression="SET last_test_date = :date, hours_since_test = :hours, updated_at = :now",
        expression_values={
            ':date': test_date,
            ':hours': hours_since_test,
            ':now': datetime.now().isoformat()
        }
    )

def process_csv_file(bucket: str, key: str) -> Dict[str, int]:
    """Process a CSV file from S3."""
    stats = {
        'processed': 0,
        'errors': 0
    }
    
    try:
        # Get file from S3
        response = s3_client.get_object(Bucket=bucket, Key=key)
        csv_content = response['Body'].read().decode('utf-8')
        df = pd.read_csv(StringIO(csv_content))
        records = df.to_dict('records')
        
        # Determine file type (PMS or LIS) based on columns
        is_pms = all(col in df.columns for col in ['patient_id', 'first_name', 'last_name'])
        
        for record in records:
            try:
                if is_pms:
                    # Process PMS record
                    patient, admission = process_pms_record(record)
                    patients_table.put_item(patient)
                    if admission:
                        admissions_table.put_item(admission)
                else:
                    # Process LIS record
                    test = process_lis_record(record)
                    tests_table.put_item(test)
                    # Update admission's last test date
                    update_admission_test_date(test.admission_id, test.test_date)
                
                stats['processed'] += 1
                    
            except Exception as e:
                stats['errors'] += 1
                logger.error(f"Error processing record: {str(e)}", 
                           extra={
                               "record": record,
                               "error": str(e)
                           })
                continue

        return stats

    except Exception as e:
        logger.error(f"Error processing file: {str(e)}", 
                    extra={
                        "bucket": bucket,
                        "key": key,
                        "error": str(e)
                    })
        raise

@logger.inject_lambda_context
def handle(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Handle S3 event trigger."""
    try:
        # Process each record in the event
        results = []
        for record in event['Records']:
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            
            logger.info(f"Processing file", extra={"bucket": bucket, "key": key})
            
            stats = process_csv_file(bucket, key)
            results.append({
                'file': key,
                'stats': stats
            })
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Processing complete',
                'results': results
            })
        }
        
    except Exception as e:
        logger.error(f"Error in handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }