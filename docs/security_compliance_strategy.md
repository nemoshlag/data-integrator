# Security and Compliance Strategy for Healthcare Data

## 1. Data Encryption

### 1.1 Encryption at Rest
```yaml
# Aurora Cluster Configuration
encryption:
  storage:
    enabled: true
    kms_key: ${self:custom.kms.key_arn}
    
  backups:
    enabled: true
    kms_key: ${self:custom.kms.backup_key_arn}
    
  logs:
    enabled: true
    kms_key: ${self:custom.kms.log_key_arn}
```

### 1.2 Encryption in Transit
```python
class DatabaseConnection:
    def __init__(self):
        self.ssl_config = {
            'sslmode': 'verify-full',
            'sslcert': '/etc/certs/client-cert.pem',
            'sslkey': '/etc/certs/client-key.pem',
            'sslrootcert': '/etc/certs/ca.pem'
        }
    
    async def get_connection(self):
        return await asyncpg.connect(
            dsn=config.DATABASE_URL,
            **self.ssl_config
        )
```

## 2. Access Control

### 2.1 Database Roles and Permissions
```sql
-- Create application roles
CREATE ROLE readonly;
CREATE ROLE dataentry;
CREATE ROLE admin;

-- Basic permissions
GRANT CONNECT ON DATABASE hospital_monitor TO readonly, dataentry, admin;
GRANT USAGE ON SCHEMA public TO readonly, dataentry, admin;

-- Read-only permissions
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;

-- Data entry permissions
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO dataentry;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO dataentry;

-- Admin permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO admin;

-- Row Level Security
ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
ALTER TABLE admissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE tests ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY patient_access ON patients
    USING (department_id = current_user_department());

CREATE POLICY admission_access ON admissions
    USING (department_id = current_user_department());

CREATE POLICY test_access ON tests
    USING (department_id = current_user_department());
```

### 2.2 Authentication Management
```python
class AuthManager:
    def __init__(self):
        self.secret_manager = boto3.client('secretsmanager')
    
    async def rotate_credentials(self):
        """Rotate database credentials."""
        try:
            new_password = self.generate_secure_password()
            
            # Update in Secrets Manager
            await self.secret_manager.update_secret(
                SecretId=config.DB_SECRET_ARN,
                SecretString=json.dumps({
                    'username': config.DB_USERNAME,
                    'password': new_password
                })
            )
            
            # Update in database
            async with self.get_admin_connection() as conn:
                await conn.execute(f"""
                    ALTER USER {config.DB_USERNAME} 
                    WITH PASSWORD '{new_password}'
                """)
            
            return True
            
        except Exception as e:
            logger.error(f"Credential rotation failed: {str(e)}")
            return False
    
    def generate_secure_password(self) -> str:
        """Generate cryptographically secure password."""
        return secrets.token_urlsafe(32)
```

## 3. Audit Logging

### 3.1 Database Auditing
```sql
-- Create audit log table
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    table_name TEXT NOT NULL,
    record_id TEXT NOT NULL,
    old_data JSONB,
    new_data JSONB,
    ip_address INET,
    user_agent TEXT
);

-- Create audit trigger function
CREATE OR REPLACE FUNCTION audit_trigger_func()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (
        user_id,
        action,
        table_name,
        record_id,
        old_data,
        new_data,
        ip_address
    )
    VALUES (
        current_user,
        TG_OP,
        TG_TABLE_NAME,
        CASE
            WHEN TG_OP = 'DELETE' THEN OLD.id::text
            ELSE NEW.id::text
        END,
        CASE
            WHEN TG_OP = 'DELETE' THEN to_jsonb(OLD)
            WHEN TG_OP = 'UPDATE' THEN to_jsonb(OLD)
            ELSE NULL
        END,
        CASE
            WHEN TG_OP IN ('INSERT', 'UPDATE') THEN to_jsonb(NEW)
            ELSE NULL
        END,
        inet_client_addr()
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply audit triggers
CREATE TRIGGER audit_patients_trigger
AFTER INSERT OR UPDATE OR DELETE ON patients
FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

CREATE TRIGGER audit_admissions_trigger
AFTER INSERT OR UPDATE OR DELETE ON admissions
FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

CREATE TRIGGER audit_tests_trigger
AFTER INSERT OR UPDATE OR DELETE ON tests
FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();
```

### 3.2 Application Logging
```python
class SecurityLogger:
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
        self.log_group = f"/aws/rds/cluster/{config.CLUSTER_ID}/security"
    
    async def log_security_event(self, event_type: str, details: dict):
        """Log security-related events."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'details': details,
            'user': current_user.id,
            'ip_address': request.remote_addr,
            'user_agent': request.user_agent.string
        }
        
        await self.cloudwatch.put_log_events(
            logGroupName=self.log_group,
            logStreamName=datetime.utcnow().strftime('%Y/%m/%d'),
            logEvents=[{
                'timestamp': int(time.time() * 1000),
                'message': json.dumps(log_entry)
            }]
        )
```

## 4. Compliance Requirements

### 4.1 HIPAA Compliance
```yaml
hipaa_controls:
  encryption:
    - Data at rest encryption using AWS KMS
    - TLS 1.2+ for data in transit
    - Encrypted backups
    
  access_control:
    - Role-based access control (RBAC)
    - Multi-factor authentication (MFA)
    - Regular access reviews
    - Principle of least privilege
    
  audit:
    - Comprehensive audit logging
    - Log retention for 6 years
    - Tamper-evident logging
    
  backup:
    - Daily automated backups
    - Monthly backup testing
    - Offsite backup storage
```

### 4.2 Data Retention
```sql
-- Create retention policy function
CREATE OR REPLACE FUNCTION apply_retention_policy()
RETURNS void AS $$
BEGIN
    -- Archive old audit logs
    INSERT INTO audit_log_archive
    SELECT *
    FROM audit_log
    WHERE timestamp < CURRENT_DATE - INTERVAL '6 years';
    
    -- Delete archived records
    DELETE FROM audit_log
    WHERE timestamp < CURRENT_DATE - INTERVAL '6 years';
    
    -- Archive old test results
    INSERT INTO tests_archive
    SELECT *
    FROM tests
    WHERE test_date < CURRENT_DATE - INTERVAL '6 years';
    
    -- Delete archived tests
    DELETE FROM tests
    WHERE test_date < CURRENT_DATE - INTERVAL '6 years';
END;
$$ LANGUAGE plpgsql;
```

## 5. Security Monitoring

### 5.1 Real-time Alerts
```python
class SecurityMonitor:
    def __init__(self):
        self.sns = boto3.client('sns')
        self.topic_arn = config.SECURITY_ALERT_TOPIC
    
    async def monitor_security_events(self):
        """Monitor for security-related events."""
        events = await self.get_security_events()
        
        for event in events:
            if self.is_security_threat(event):
                await self.send_alert(event)
    
    def is_security_threat(self, event: dict) -> bool:
        """Analyze event for security threats."""
        return any([
            event['failed_login_attempts'] > 5,
            event['unusual_access_pattern'],
            event['unauthorized_table_access'],
            event['suspicious_query_pattern']
        ])
    
    async def send_alert(self, event: dict):
        """Send security alert."""
        await self.sns.publish(
            TopicArn=self.topic_arn,
            Subject=f"Security Alert: {event['type']}",
            Message=json.dumps(event, indent=2)
        )
```

### 5.2 Compliance Reporting
```python
class ComplianceReporter:
    async def generate_compliance_report(self, start_date: datetime, end_date: datetime):
        """Generate compliance report."""
        report = {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'access_control': await self.audit_access_control(),
            'data_encryption': await self.audit_encryption(),
            'audit_logs': await self.audit_logging(),
            'security_incidents': await self.get_security_incidents(),
            'compliance_violations': await self.get_compliance_violations()
        }
        
        # Store report
        await self.store_compliance_report(report)
        
        # Send notifications
        if report['compliance_violations']:
            await self.notify_compliance_team(report)
        
        return report
```

This security and compliance strategy ensures that our PostgreSQL serverless architecture meets HIPAA requirements and maintains the confidentiality, integrity, and availability of healthcare data.