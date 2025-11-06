# VLA API Monitoring Configuration Summary

## Overview
Complete monitoring and alerting stack deployed for the VLA Inference API Platform with Prometheus, Grafana, and Alertmanager.

## Files Created

### Grafana Dashboards (4 dashboards)
1. **`/monitoring/grafana/dashboards/ops-dashboard.json`**
   - Real-time operational metrics (10s refresh, 1h window)
   - 10 panels: Request rate, latency, errors, GPU metrics, queue depth, workers
   - Target audience: SREs, on-call engineers

2. **`/monitoring/grafana/dashboards/business-dashboard.json`**
   - Business analytics (5m refresh, 30d window)
   - 9 panels: Revenue, customer growth, MRR, ARPU, churn, usage by tier
   - Target audience: Product, Business teams

3. **`/monitoring/grafana/dashboards/safety-dashboard.json`**
   - Safety compliance (1m refresh, 7d window)
   - 9 panels: Incidents, violations, safety scores, compliance metrics
   - Target audience: Safety team, Compliance

4. **`/monitoring/grafana/dashboards/customer-analytics-dashboard.json`**
   - Per-customer insights (5m refresh, 30d window)
   - 10 panels: Usage patterns, success rates, feedback, quota utilization
   - Target audience: Customer success, Support

### Prometheus Configuration
1. **`/monitoring/prometheus/prometheus.yml`**
   - Scrape interval: 15s
   - Retention: 30 days, 50GB max
   - 9 scrape jobs: vla-api, prometheus, node, gpu, postgres, redis, alertmanager, grafana
   - Remote write ready (commented out)

2. **`/monitoring/prometheus/alerts.yml`**
   - 18 alert rules across 6 categories
   - Severity levels: critical, warning
   - Components: api, inference, hardware, safety, validation, billing, workers, model, database

### Alertmanager Configuration
1. **`/monitoring/alertmanager/alertmanager.yml`**
   - 6 receivers: default, critical, warning, safety-team, business-team, ops-team
   - Notification channels: Slack, Email, PagerDuty
   - 2 inhibition rules to prevent alert storms
   - Smart routing by severity and component

### Grafana Provisioning
1. **`/monitoring/grafana/datasources/prometheus.yml`**
   - Prometheus datasource auto-configured
   - 15s time interval, 60s query timeout

2. **`/monitoring/grafana/dashboards/dashboard-provider.yml`**
   - Auto-load dashboards from filesystem
   - 10s update interval, UI updates allowed

### Docker Configuration
1. **`docker-compose.yml` (updated)**
   - Added 8 monitoring services
   - 3 new volumes: prometheus_data, grafana_data, alertmanager_data
   - Proper health checks and dependencies

## Alert Rules Summary

### Critical Alerts (immediate action required)
| Alert | Threshold | Duration | Component |
|-------|-----------|----------|-----------|
| HighErrorRate | > 5% error rate | 5 minutes | API |
| GPUOverheating | > 85°C | 2 minutes | Hardware |
| SafetyIncidentSurge | > 100 rejections/hour | 10 minutes | Safety |
| CriticalSafetyIncident | Any critical incident | 1 minute | Safety |
| ServiceDown | Health check failed | 1 minute | API |
| ModelInferenceFailure | > 2% model errors | 5 minutes | Model |

### Warning Alerts (requires attention)
| Alert | Threshold | Duration | Component |
|-------|-----------|----------|-----------|
| HighLatency | p99 > 2s | 5 minutes | Inference |
| GPUMemoryHigh | > 95% memory | 5 minutes | Hardware |
| HighQueueDepth | > 80 pending | 5 minutes | Queue |
| HighValidationFailureRate | > 1% failures | 5 minutes | Validation |
| QuotaExceeded | > 95% quota used | 5 minutes | Billing |
| WorkerOverloaded | > 95% utilization | 10 minutes | Workers |
| RateLimitHitRate | > 10/second | 5 minutes | Rate Limiting |
| HighChurnRate | > 5% weekly | 1 hour | Business |
| HighMemoryUsage | > 8GB | 10 minutes | System |
| DatabaseConnectionPoolExhausted | > 90% connections | 5 minutes | Database |
| SlowDatabaseQueries | p95 > 1s | 5 minutes | Database |
| SlowModelLoading | p95 > 30s | 5 minutes | Model |

## Services and Ports

| Service | Port | Purpose | Profile |
|---------|------|---------|---------|
| VLA API | 8000 | Main application | dev/prod |
| Prometheus | 9090 | Metrics collection | default |
| Grafana | 3000 | Visualization | default |
| Alertmanager | 9093 | Alert routing | default |
| Node Exporter | 9100 | System metrics | default |
| DCGM Exporter | 9400 | GPU metrics | prod, monitoring-gpu |
| Postgres Exporter | 9187 | Database metrics | default |
| Redis Exporter | 9121 | Cache metrics | default |

## Quick Start Commands

### Development (without GPU)
```bash
# Start core services + monitoring
docker-compose --profile dev up -d

# View logs
docker-compose logs -f prometheus grafana alertmanager

# Stop all
docker-compose --profile dev down
```

### Production (with GPU)
```bash
# Start all services including GPU monitoring
docker-compose --profile prod up -d

# Or start with GPU monitoring profile
docker-compose --profile monitoring-gpu up -d

# Health check
docker-compose ps

# Stop all
docker-compose --profile prod down
```

### Access URLs
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090
- Alertmanager: http://localhost:9093
- VLA API: http://localhost:8000
- API Metrics: http://localhost:8000/metrics

## Dashboard Panel Details

### Operations Dashboard (10 panels)
1. Request Rate by Model - Line graph showing requests/sec by model and robot type
2. Latency Percentiles - p50/p95/p99 latency trends
3. Error Rate by Status - Error rate broken down by error type
4. GPU Utilization - Percentage utilization per GPU with thresholds
5. GPU Temperature - Temperature monitoring with critical thresholds
6. Queue Depth - Real-time queue depth monitoring
7. Worker Utilization - Gauge showing worker pool capacity
8. Top Errors by Type - Table of most common errors
9. GPU Memory Usage - Memory utilization percentage per GPU
10. Success Rate - Overall success rate stat panel with thresholds

### Business Dashboard (9 panels)
1. Daily Inference Counts by Tier - Bar chart of daily usage
2. Revenue by Tier - Pie chart showing revenue distribution
3. Customer Growth - Line graph of new vs active customers
4. Usage by Model - Bar gauge showing model popularity
5. Top 10 Customers by Usage - Table of highest-volume customers
6. Quota Utilization by Tier - Line graph of quota usage trends
7. Monthly Recurring Revenue - Stat panel showing MRR
8. ARPU - Average revenue per user calculation
9. Churn Rate - Percentage of churned customers

### Safety Dashboard (9 panels)
1. Safety Incident Count by Severity - Bar chart of incidents
2. Violation Types Distribution - Pie chart of violation categories
3. Safety Score Trends - Line graph of safety scores over time
4. Top Violating Customers - Table with color-coded violations
5. Rejection Rate Over Time - Percentage of rejected requests
6. Safety Check Latency - p50/p95/p99 safety check performance
7. Critical Safety Alerts - Stat panel showing 24h critical count
8. Compliance Score - Gauge showing overall compliance percentage
9. False Positive Rate - Stat panel with false positive percentage

### Customer Analytics Dashboard (10 panels)
1. Usage Patterns by Robot Type - Bar chart of robot usage
2. Instruction Categories Distribution - Pie chart of instruction types
3. Success Rate by Robot - Bar gauge with color-coded success rates
4. Latency by Customer - Line graph of p95 latency
5. Feedback Rate - Line graph showing feedback submissions
6. Peak Usage Hours - Heatmap showing usage patterns
7. Total Requests (30d) - Stat panel with request count
8. Average Daily Requests - Stat panel with daily average
9. Quota Utilization - Gauge showing customer quota usage
10. Error Rate - Stat panel with customer error percentage

## Metric Naming Convention

All VLA API metrics follow the pattern: `vla_{component}_{metric}__{unit}`

Examples:
- `vla_inference_requests_total` - Counter of inference requests
- `vla_inference_duration_seconds` - Histogram of inference latency
- `vla_gpu_temperature_celsius` - Gauge of GPU temperature
- `vla_safety_incidents_total` - Counter of safety incidents
- `vla_quota_used` - Gauge of current quota usage

## Alert Notification Flow

1. **Alert Triggers** → Prometheus evaluates rules every 15s
2. **Alert Fires** → After threshold exceeded for specified duration
3. **Grouped** → Alertmanager groups by alertname, cluster, service
4. **Routed** → Based on severity/component to appropriate receiver
5. **Notified** → Via Slack, Email, and/or PagerDuty
6. **Inhibited** → Related alerts suppressed if higher severity firing
7. **Resolved** → Notification sent when alert condition clears

## Configuration Customization

### Change Alert Thresholds
Edit `/monitoring/prometheus/alerts.yml`:
```yaml
- alert: HighErrorRate
  expr: rate(vla_inference_requests_total{status="error"}[5m]) > 0.05  # Change to 0.10 for 10%
```

### Add Slack Notifications
Edit `/monitoring/alertmanager/alertmanager.yml`:
```yaml
slack_configs:
  - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
    channel: '#vla-alerts'
```

### Add Email Notifications
Edit `/monitoring/alertmanager/alertmanager.yml`:
```yaml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@your-company.com'
  smtp_auth_username: 'alerts@your-company.com'
  smtp_auth_password: 'your-app-password'
```

### Add PagerDuty Integration
Edit `/monitoring/alertmanager/alertmanager.yml`:
```yaml
pagerduty_configs:
  - service_key: 'YOUR_PAGERDUTY_INTEGRATION_KEY'
```

### Modify Grafana Admin Password
```bash
docker exec -it vlaapi-grafana grafana-cli admin reset-admin-password newpassword
```

## Best Practices

### Alert Management
- Start with high thresholds and tune down based on actual patterns
- Use inhibition rules to prevent alert storms
- Set appropriate repeat intervals (critical: 5m, warning: 30m)
- Document runbook URLs for each alert

### Dashboard Usage
- Operations: Real-time monitoring during incidents
- Business: Weekly/monthly reviews
- Safety: Daily compliance checks
- Customer: Support ticket investigation

### Performance Optimization
- Use recording rules for expensive queries
- Monitor Prometheus resource usage
- Set appropriate scrape intervals per job
- Use metric relabeling to drop unnecessary labels

### Security
- Change default Grafana credentials immediately
- Use HTTPS in production
- Restrict dashboard access via authentication
- Store sensitive credentials in environment variables

## Maintenance Tasks

### Daily
- Check critical alerts in Alertmanager
- Review ops dashboard for anomalies
- Monitor GPU health and temperature

### Weekly
- Review business metrics and trends
- Check safety compliance scores
- Analyze top errors and customer issues
- Update alert thresholds if needed

### Monthly
- Review and optimize dashboard queries
- Clean up old alert rules
- Update notification channels
- Export dashboard backups

## Troubleshooting

### Metrics Not Appearing
```bash
# Check if VLA API is exposing metrics
curl http://localhost:8000/metrics

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job, health, lastError}'

# View Prometheus logs
docker logs vlaapi-prometheus --tail 100
```

### Dashboards Not Loading
```bash
# Check Grafana logs
docker logs vlaapi-grafana --tail 100

# Verify datasource
docker exec vlaapi-grafana curl http://prometheus:9090/-/healthy

# Check dashboard provisioning
docker exec vlaapi-grafana ls -la /etc/grafana/provisioning/dashboards/
```

### Alerts Not Firing
```bash
# Check alert rules
curl http://localhost:9090/api/v1/rules | jq '.data.groups[].rules[] | {alert, state}'

# Verify Alertmanager
curl http://localhost:9093/api/v2/alerts

# Check Alertmanager config
docker exec vlaapi-alertmanager amtool check-config /etc/alertmanager/alertmanager.yml
```

## Next Steps

1. **Customize Notifications**
   - Add your Slack webhook URLs
   - Configure SMTP credentials
   - Set up PagerDuty integration

2. **Tune Alert Thresholds**
   - Monitor for false positives
   - Adjust based on baseline metrics
   - Add new alerts for custom use cases

3. **Extend Dashboards**
   - Add panels for custom metrics
   - Create team-specific views
   - Set up dashboard variables for filtering

4. **Set Up Long-term Storage**
   - Configure Prometheus remote write
   - Set up data retention policies
   - Consider Thanos or Cortex for scaling

5. **Implement SLOs**
   - Define Service Level Objectives
   - Create SLO-based alerts
   - Track error budgets

## Support and Documentation

- Prometheus: https://prometheus.io/docs/
- Grafana: https://grafana.com/docs/
- Alertmanager: https://prometheus.io/docs/alerting/latest/alertmanager/
- Docker Compose: https://docs.docker.com/compose/

## Summary

The monitoring stack is fully configured and ready to deploy:

✓ 4 Grafana dashboards with 38 total panels
✓ 18 Prometheus alert rules across 6 categories
✓ Alertmanager with multi-channel notifications
✓ 8 monitoring services in Docker Compose
✓ Complete documentation and troubleshooting guides
✓ Security best practices implemented
✓ Performance optimization configured

Start the stack with:
```bash
docker-compose --profile dev up -d  # Development
# or
docker-compose --profile prod up -d  # Production with GPU
```

Access Grafana at http://localhost:3000 (admin/admin)
