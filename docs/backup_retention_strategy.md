# Backup and Data Retention Strategy

## 1. Backup Configuration

### 1.1 AWS RDS Backup Settings
```yaml
# serverless.yml
resources:
  AuroraCluster:
    Type: AWS::RDS::DBCluster
    Properties:
      BackupRetentionPeriod: 35  # Days to retain automated backups
      PreferredBackupWindow: "03:00-04:00"
      PreferredMaintenanceWindow: "Mon:04:00-Mon:05:00"
      EnableCloudwatchLogsExports:
        - postgresql
        - upgrade
      BackupTarget: REGION
      CopyTagsToSnapshot: true
      DeletionProtection: true
      StorageEncrypted: true
      KmsKeyId: ${self:custom.kms.key_arn}
```

### 1.2 Backup Types and Schedule
```yaml
backup_strategy:
  automated:
    frequency: daily
    retention: 35 days
    type: incremental
    window: "03:00-04:00 UTC"
    
  manual:
    frequency: weekly
    retention: 180 days
    type: full
    schedule: "Sunday 02:00 UTC"
    
  snapshot:
    frequency: monthly
    retention: 6 years  # HIPAA compliance
    type: full
    schedule: "1st day of month 01:00 UTC"
    
  logical:
    frequency: weekly
    retention: 90 days
    type: pg_dump
    schedule: "Saturday 02:00 UTC"
```

## 2. Backup Implementation

### 2.1 Automated Backup Manager
```python
class BackupManager:
    def __init__(self):
        self.rds = boto3.client('rds')
        self.s3 = boto3.client('s3')
        self.sns = boto3.client('sns')
    
    async def create_manual_snapshot(self, description: str):
        """Create manual DB snapshot."""
        try:
            response = await self.rds.create_db_cluster_snapshot(
                DBClusterSnapshotIdentifier=(
                    f"{config.CLUSTER_ID}-manual-"
                    f"{datetime.now().strftime('%Y-%m-%d-%H-%M')}"
                ),
                DBClusterIdentifier=config.CLUSTER_ID,
                Tags=[
                    {
                        'Key': 'BackupType',
                        'Value': 'Manual'
                    },
                    {
                        'Key': 'Description',
                        'Value': description
                    }
                ]
            )
            
            await self._monitor_snapshot_progress(
                response['DBClusterSnapshot']['DBClusterSnapshotIdentifier']
            )
            
            return response['DBClusterSnapshot']
            
        except Exception as e:
            await self._send_backup_alert(
                "Manual Snapshot Creation Failed",
                str(e)
            )
            raise
    
    async def perform_logical_backup(self):
        """Create logical backup using pg_dump."""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M')
            backup_file = f"logical-backup-{timestamp}.sql"
            
            # Execute pg_dump
            cmd = [
                'pg_dump',
                '-h', config.DB_HOST,
                '-U', config.DB_USERNAME,
                '-d', config.DB_NAME,
                '-F', 'c',  # Custom format
                '-Z', '9',  # Maximum compression
                '-f', backup_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                env={'PGPASSWORD': config.DB_PASSWORD}
            )
            
            await process.communicate()
            
            if process.returncode == 0:
                # Upload to S3
                await self._upload_to_s3(
                    backup_file,
                    f"logical-backups/{backup_file}"
                )
            else:
                raise Exception("pg_dump failed")
                
        except Exception as e:
            await self._send_backup_alert(
                "Logical Backup Failed",
                str(e)
            )
            raise
```

## 3. Retention Policy Implementation

### 3.1 Data Lifecycle Rules
```yaml
# S3 Lifecycle Rules
lifecycle_rules:
  - prefix: automated-backups/
    transition_to_glacier: 90 days
    expire: 35 days
    
  - prefix: manual-backups/
    transition_to_glacier: 90 days
    expire: 180 days
    
  - prefix: logical-backups/
    transition_to_glacier: 90 days
    expire: 90 days
    
  - prefix: compliance-backups/
    transition_to_glacier: 90 days
    expire: 2190 days  # 6 years for HIPAA
```

### 3.2 Retention Manager
```python
class RetentionManager:
    def __init__(self):
        self.rds = boto3.client('rds')
        self.s3 = boto3.client('s3')
    
    async def apply_retention_policies(self):
        """Apply retention policies to backups."""
        await asyncio.gather(
            self._cleanup_automated_snapshots(),
            self._cleanup_manual_snapshots(),
            self._cleanup_logical_backups()
        )
    
    async def _cleanup_automated_snapshots(self):
        """Clean up automated snapshots beyond retention period."""
        snapshots = await self.rds.describe_db_cluster_snapshots(
            SnapshotType='automated',
            DBClusterIdentifier=config.CLUSTER_ID
        )
        
        retention_date = datetime.now() - timedelta(days=35)
        
        for snapshot in snapshots['DBClusterSnapshots']:
            if snapshot['SnapshotCreateTime'] < retention_date:
                await self.rds.delete_db_cluster_snapshot(
                    DBClusterSnapshotIdentifier=snapshot['DBClusterSnapshotIdentifier']
                )
```

## 4. Recovery Procedures

### 4.1 Point-in-Time Recovery
```python
class RecoveryManager:
    async def restore_to_point_in_time(
        self,
        timestamp: datetime,
        target_cluster_id: str
    ):
        """Perform point-in-time recovery."""
        try:
            response = await self.rds.restore_db_cluster_to_point_in_time(
                DBClusterIdentifier=target_cluster_id,
                SourceDBClusterIdentifier=config.CLUSTER_ID,
                RestoreToTime=timestamp,
                UseLatestRestorableTime=False
            )
            
            await self._monitor_restore_progress(target_cluster_id)
            await self._validate_restored_cluster(target_cluster_id)
            
            return response['DBCluster']
            
        except Exception as e:
            await self._send_recovery_alert(
                "Point-in-Time Recovery Failed",
                str(e)
            )
            raise
```

### 4.2 Recovery Testing
```python
class RecoveryTester:
    async def perform_recovery_test(self):
        """Perform periodic recovery testing."""
        test_cluster_id = f"{config.CLUSTER_ID}-recovery-test"
        
        try:
            # Restore from latest snapshot
            await self.restore_from_latest_snapshot(test_cluster_id)
            
            # Run validation tests
            validation_results = await self.validate_restored_data(test_cluster_id)
            
            # Generate test report
            report = self.generate_test_report(validation_results)
            
            # Store test results
            await self.store_test_results(report)
            
            return report
            
        finally:
            # Cleanup test cluster
            await self.cleanup_test_cluster(test_cluster_id)
    
    async def validate_restored_data(self, cluster_id: str):
        """Validate restored data integrity."""
        validations = [
            self._check_record_counts(),
            self._verify_recent_transactions(),
            self._check_data_integrity(),
            self._verify_permissions()
        ]
        
        return await asyncio.gather(*validations)
```

## 5. Compliance Documentation

### 5.1 Backup Verification
```python
class BackupVerification:
    async def verify_backup_compliance(self):
        """Verify backup compliance requirements."""
        verifications = {
            'encryption': await self._verify_encryption(),
            'retention': await self._verify_retention_periods(),
            'completion': await self._verify_backup_completion(),
            'accessibility': await self._verify_backup_accessibility(),
            'integrity': await self._verify_backup_integrity()
        }
        
        # Generate compliance report
        report = {
            'timestamp': datetime.now().isoformat(),
            'verifications': verifications,
            'compliance_status': all(verifications.values()),
            'remediation_needed': not all(verifications.values())
        }
        
        # Store report for audit purposes
        await self._store_compliance_report(report)
        
        return report
```

This backup and retention strategy ensures data durability, HIPAA compliance, and reliable recovery capabilities while maintaining system performance and data integrity.