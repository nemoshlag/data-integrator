# Operational Runbook for PostgreSQL Serverless

## 1. Daily Operations

### 1.1 Health Check Procedures
```bash
#!/bin/bash
# health_check.sh

# Check database connectivity
psql -h ${DB_HOST} -U ${DB_USER} -d ${DB_NAME} -c "SELECT 1"

# Check replication lag
psql -h ${DB_HOST} -U ${DB_USER} -d ${DB_NAME} -c "
SELECT client_addr, 
       state,
       sent_lsn,
       write_lsn,
       flush_lsn,
       replay_lsn,
       pg_wal_lsn_diff(sent_lsn, replay_lsn) AS lag_bytes
FROM pg_stat_replication;"

# Check long-running queries
psql -h ${DB_HOST} -U ${DB_USER} -d ${DB_NAME} -c "
SELECT pid, 
       now() - pg_stat_activity.query_start AS duration,
       query
FROM pg_stat_activity
WHERE state = 'active'
  AND now() - pg_stat_activity.query_start > interval '5 minutes';"
```

### 1.2 Performance Monitoring
```python
class PerformanceMonitor:
    def __init__(self):
        self.metrics = []
        self.alerts = []
    
    async def daily_performance_check(self):
        """Run daily performance checks."""
        checks = {
            'connection_count': self._check_connections(),
            'query_performance': self._check_query_performance(),
            'storage_usage': self._check_storage(),
            'cache_hit_ratio': self._check_cache(),
            'cpu_usage': self._check_cpu()
        }
        
        await asyncio.gather(*[check() for check in checks.values()])
        
        # Generate daily report
        report = self._generate_report()
        await self._store_report(report)
        
        return report
    
    async def _check_connections(self):
        """Check connection statistics."""
        query = """
            SELECT count(*) as total_connections,
                   sum(case when state = 'active' then 1 else 0 end) as active_connections,
                   sum(case when state = 'idle' then 1 else 0 end) as idle_connections
            FROM pg_stat_activity;
        """
        return await self.execute_query(query)
```

## 2. Maintenance Procedures

### 2.1 Vacuum and Analyze
```python
class MaintenanceManager:
    async def perform_vacuum(self, table_name: str = None):
        """Perform VACUUM operation."""
        try:
            if table_name:
                query = f"VACUUM ANALYZE {table_name};"
            else:
                query = "VACUUM ANALYZE;"
            
            start_time = time.time()
            await self.execute_query(query)
            duration = time.time() - start_time
            
            await self.log_maintenance({
                'operation': 'vacuum',
                'table': table_name,
                'duration': duration,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            await self.alert_maintenance_failure('vacuum', str(e))
            raise

    async def analyze_table_bloat(self):
        """Analyze table bloat."""
        query = """
            SELECT schemaname, tablename, 
                   pg_size_pretty(bloat_size) as bloat_size,
                   round(bloat_ratio::numeric, 2) as bloat_ratio
            FROM (
                SELECT schemaname, tablename,
                       pg_total_relation_size(table_oid) as total_size,
                       pg_table_size(table_oid) as table_size,
                       pg_total_relation_size(table_oid) - pg_table_size(table_oid) as bloat_size,
                       round(100 * (pg_total_relation_size(table_oid) - pg_table_size(table_oid))::numeric / pg_total_relation_size(table_oid), 2) as bloat_ratio
                FROM (
                    SELECT schemaname, tablename, 'public.' || tablename::regclass::oid as table_oid
                    FROM pg_tables
                    WHERE schemaname = 'public'
                ) t
            ) s
            WHERE bloat_ratio > 20
            ORDER BY bloat_ratio DESC;
        """
        return await self.execute_query(query)
```

### 2.2 Index Maintenance
```sql
-- Create index maintenance functions
CREATE OR REPLACE FUNCTION maintain_indexes()
RETURNS TABLE (
    index_name text,
    table_name text,
    action text,
    before_size text,
    after_size text
) AS $$
DECLARE
    idx record;
BEGIN
    FOR idx IN
        SELECT schemaname, tablename, indexrelname
        FROM pg_stat_user_indexes
        WHERE idx_scan = 0
        AND pg_relation_size(indexrelid) > 10 * 1024 * 1024  -- > 10MB
    LOOP
        EXECUTE format('ALTER INDEX %I.%I SET STATISTICS 1000',
                      idx.schemaname, idx.indexrelname);
                      
        RETURN QUERY
        SELECT idx.indexrelname::text,
               idx.tablename::text,
               'REINDEX'::text,
               pg_size_pretty(pg_relation_size(idx.indexrelname::regclass))::text,
               pg_size_pretty(pg_relation_size(idx.indexrelname::regclass))::text;
    END LOOP;
END;
$$ LANGUAGE plpgsql;
```

## 3. Troubleshooting Procedures

### 3.1 Connection Issues
```python
class ConnectionTroubleshooter:
    async def diagnose_connection_issues(self):
        """Diagnose connection-related issues."""
        diagnostics = {
            'current_connections': await self._get_connection_count(),
            'connection_states': await self._get_connection_states(),
            'max_connections': await self._get_max_connections(),
            'connection_duration': await self._get_connection_duration()
        }
        
        # Check for common issues
        issues = []
        
        if diagnostics['current_connections'] > 0.8 * diagnostics['max_connections']:
            issues.append('High connection usage')
        
        if diagnostics['connection_states'].get('idle_in_transaction', 0) > 10:
            issues.append('High number of idle transactions')
        
        return {
            'diagnostics': diagnostics,
            'issues': issues,
            'recommendations': self._generate_recommendations(issues)
        }
```

### 3.2 Performance Issues
```python
class PerformanceTroubleshooter:
    async def analyze_performance_issue(self):
        """Analyze performance-related issues."""
        metrics = {
            'slow_queries': await self._get_slow_queries(),
            'cache_stats': await self._get_cache_stats(),
            'io_stats': await self._get_io_stats(),
            'index_usage': await self._get_index_usage(),
            'table_stats': await self._get_table_stats()
        }
        
        # Generate analysis
        analysis = self._analyze_metrics(metrics)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(analysis)
        
        return {
            'metrics': metrics,
            'analysis': analysis,
            'recommendations': recommendations
        }
    
    async def _get_slow_queries(self):
        """Get information about slow queries."""
        query = """
            SELECT query,
                   calls,
                   total_exec_time / calls as avg_exec_time,
                   rows / calls as avg_rows,
                   100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) as cache_hit_ratio
            FROM pg_stat_statements
            WHERE total_exec_time / calls > 100  -- ms
            ORDER BY total_exec_time DESC
            LIMIT 10;
        """
        return await self.execute_query(query)
```

## 4. Emergency Procedures

### 4.1 High Load Response
```python
class EmergencyResponder:
    async def handle_high_load(self):
        """Handle high load situations."""
        steps = [
            self._terminate_long_queries,
            self._cancel_conflicting_operations,
            self._increase_resources,
            self._notify_team
        ]
        
        for step in steps:
            try:
                await step()
            except Exception as e:
                await self.log_error(f"Emergency step failed: {str(e)}")
    
    async def _terminate_long_queries(self):
        """Terminate queries running longer than threshold."""
        query = """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE state = 'active'
              AND now() - query_start > interval '30 minutes'
              AND query NOT LIKE '%pg_terminate_backend%';
        """
        await self.execute_query(query)
```

### 4.2 Failover Procedures
```python
class FailoverManager:
    async def initiate_failover(self):
        """Initiate manual failover process."""
        steps = {
            'pre_failover': [
                self._check_replica_status,
                self._verify_replication_lag,
                self._backup_critical_state
            ],
            'failover': [
                self._promote_replica,
                self._update_endpoints,
                self._verify_promotion
            ],
            'post_failover': [
                self._verify_applications,
                self._update_monitoring,
                self._notify_team
            ]
        }
        
        for phase, phase_steps in steps.items():
            for step in phase_steps:
                try:
                    await step()
                except Exception as e:
                    await self._handle_failover_error(phase, step, e)
                    raise
```

## 5. Monitoring and Alerts

### 5.1 Alert Configuration
```yaml
alerts:
  high_cpu:
    threshold: 80
    duration: 5m
    action: notify_team
    
  connection_limit:
    threshold: 80%
    duration: 5m
    action: scale_connections
    
  replication_lag:
    threshold: 300s
    duration: 5m
    action: notify_dba
    
  disk_usage:
    threshold: 85%
    duration: 10m
    action: cleanup_data
```

### 5.2 Response Procedures
```yaml
response_procedures:
  high_load:
    - Check active queries
    - Identify resource bottlenecks
    - Consider scaling options
    - Notify team if persistent
    
  connection_issues:
    - Check connection count
    - Identify connection sources
    - Review connection pooling
    - Reset idle connections
    
  replication_issues:
    - Check replication lag
    - Verify network connectivity
    - Review write load
    - Consider scaling read replicas
```

This runbook provides comprehensive guidance for managing and troubleshooting our PostgreSQL serverless infrastructure while maintaining high availability and performance.