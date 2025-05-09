# PostgreSQL Serverless Monitoring Strategy

## 1. Key Metrics

### 1.1 Database Metrics
```sql
-- Create monitoring views
CREATE VIEW db_performance_metrics AS
SELECT 
    current_timestamp as timestamp,
    numbackends as active_connections,
    xact_commit + xact_rollback as total_transactions,
    ROUND(xact_commit::numeric / (xact_commit + xact_rollback) * 100, 2) as commit_ratio,
    blks_hit::numeric / (blks_hit + blks_read) as cache_hit_ratio,
    conflicts as deadlock_count,
    temp_files as temp_file_count,
    temp_bytes as temp_file_size
FROM pg_stat_database
WHERE datname = current_database();

-- Table-specific metrics
CREATE VIEW table_metrics AS
SELECT
    schemaname,
    relname as table_name,
    seq_scan,
    idx_scan,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes,
    n_live_tup as live_rows,
    n_dead_tup as dead_rows,
    last_vacuum,
    last_autovacuum
FROM pg_stat_user_tables;
```

### 1.2 CloudWatch Metrics Configuration
```yaml
# serverless.yml excerpt
resources:
  Resources:
    DatabaseAlarms:
      Type: AWS::CloudWatch::Alarm
      Properties:
        AlarmName: ${self:service}-${self:provider.stage}-db-connections
        MetricName: DatabaseConnections
        Namespace: AWS/RDS
        Statistic: Average
        Period: 300
        EvaluationPeriods: 2
        Threshold: 80
        ComparisonOperator: GreaterThanThreshold
        AlarmActions: 
          - !Ref AlertsTopic
```

## 2. Application Monitoring

### 2.1 Lambda Function Instrumentation
```python
from aws_lambda_powertools import Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit
from functools import wraps

metrics = Metrics(namespace="HospitalMonitor")
tracer = Tracer()

def monitor_database(name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000
                
                metrics.add_metric(
                    name=f"{name}_duration",
                    unit=MetricUnit.Milliseconds,
                    value=duration
                )
                metrics.add_metric(
                    name=f"{name}_success",
                    unit=MetricUnit.Count,
                    value=1
                )
                
                return result
                
            except Exception as e:
                metrics.add_metric(
                    name=f"{name}_error",
                    unit=MetricUnit.Count,
                    value=1
                )
                raise
            
        return wrapper
    return decorator
```

### 2.2 Connection Pool Monitoring
```python
class MonitoredConnectionPool:
    def __init__(self, pool_config):
        self.pool = SimpleConnectionPool(**pool_config)
        self.metrics = Metrics(namespace="DatabaseConnections")
    
    async def get_connection(self):
        connection = await self.pool.getconn()
        await self._update_metrics()
        return connection
    
    async def _update_metrics(self):
        self.metrics.add_metric(
            name="active_connections",
            value=self.pool.used,
            unit=MetricUnit.Count
        )
        self.metrics.add_metric(
            name="available_connections",
            value=self.pool.free,
            unit=MetricUnit.Count
        )
```

## 3. Alerts and Notifications

### 3.1 Critical Alerts
```python
# alerts.py
from typing import Dict, Any
import boto3

sns = boto3.client('sns')

class AlertManager:
    def __init__(self, topic_arn: str):
        self.topic_arn = topic_arn
    
    async def alert_high_connection_usage(self, usage: float):
        if usage > 80:
            await self._send_alert(
                "High Database Connection Usage",
                f"Connection pool usage at {usage}%"
            )
    
    async def alert_long_running_queries(self, queries: List[Dict]):
        if any(q['duration'] > 10000 for q in queries):
            await self._send_alert(
                "Long Running Queries Detected",
                f"Found {len(queries)} queries running > 10s"
            )
    
    async def _send_alert(self, subject: str, message: str):
        sns.publish(
            TopicArn=self.topic_arn,
            Subject=subject,
            Message=message
        )
```

## 4. Performance Analysis

### 4.1 Query Performance Monitoring
```sql
-- Create performance analysis views
CREATE VIEW slow_queries AS
SELECT 
    query,
    calls,
    total_exec_time / calls as avg_exec_time,
    rows / calls as avg_rows,
    shared_blks_hit / calls as avg_cache_hits,
    shared_blks_read / calls as avg_disk_reads
FROM pg_stat_statements
WHERE total_exec_time / calls > 1000  -- queries taking > 1s
ORDER BY total_exec_time DESC;

-- Index usage analysis
CREATE VIEW index_usage AS
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as number_of_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

### 4.2 Automated Performance Reports
```python
class PerformanceAnalyzer:
    async def generate_daily_report(self):
        report = {
            'timestamp': datetime.now().isoformat(),
            'database_stats': await self._get_db_stats(),
            'slow_queries': await self._get_slow_queries(),
            'connection_stats': await self._get_connection_stats(),
            'cache_stats': await self._get_cache_stats()
        }
        
        # Store report in S3
        s3.put_object(
            Bucket=config.REPORTS_BUCKET,
            Key=f"performance/daily/{datetime.now().date()}.json",
            Body=json.dumps(report)
        )
        
        return report
```

## 5. Resource Optimization

### 5.1 Auto-scaling Configuration
```yaml
# serverless.yml excerpt
resources:
  Resources:
    AuroraCluster:
      Type: AWS::RDS::DBCluster
      Properties:
        ServerlessV2ScalingConfiguration:
          MinCapacity: ${self:custom.db.minCapacity}
          MaxCapacity: ${self:custom.db.maxCapacity}
        ScalingConfiguration:
          AutoPause: true
          MinCapacity: ${self:custom.db.minCapacity}
          MaxCapacity: ${self:custom.db.maxCapacity}
          SecondsUntilAutoPause: 3600
```

### 5.2 Automated Maintenance
```python
class DatabaseMaintenance:
    async def perform_maintenance(self):
        tasks = [
            self._vacuum_analyze(),
            self._reindex_tables(),
            self._update_statistics()
        ]
        await asyncio.gather(*tasks)
    
    async def _vacuum_analyze(self):
        for table in config.TABLES_TO_VACUUM:
            await self.execute(f"VACUUM ANALYZE {table}")
    
    async def _update_statistics(self):
        await self.execute("ANALYZE VERBOSE")
```

## 6. Dashboard Configuration

### 6.1 CloudWatch Dashboard
```yaml
# dashboards/database.yml
widgets:
  - type: metric
    properties:
      title: Database Connections
      metrics:
        - AWS/RDS/DatabaseConnections
      period: 300
      stat: Average
      
  - type: metric
    properties:
      title: Query Performance
      metrics:
        - Custom/Database/QueryDuration
      period: 60
      stat: p95
```

This monitoring strategy provides comprehensive visibility into the PostgreSQL serverless system's performance and health, enabling proactive issue detection and optimization.