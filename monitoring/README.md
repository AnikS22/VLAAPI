# VLA API Monitoring Stack

Complete monitoring and alerting solution for the VLA Inference API Platform.

## Components

### Prometheus
- **Port**: 9090
- **Purpose**: Metrics collection and storage
- **Retention**: 30 days, 50GB max
- **Scrape Interval**: 15s

### Grafana
- **Port**: 3000
- **Default Credentials**: admin/admin (change immediately)
- **Dashboards**: 4 pre-configured dashboards

### Alertmanager
- **Port**: 9093
- **Purpose**: Alert routing and notification
- **Channels**: Slack, Email, PagerDuty

### Exporters
- **Node Exporter** (9100): System metrics
- **NVIDIA DCGM Exporter** (9400): GPU metrics
- **Postgres Exporter** (9187): Database metrics
- **Redis Exporter** (9121): Cache metrics

## Quick Start

### Start Monitoring Stack (Development)
```bash
docker-compose --profile dev up -d prometheus grafana alertmanager node-exporter postgres-exporter redis-exporter
```

### Start Full Stack (Production with GPU)
```bash
docker-compose --profile prod up -d
```

### Access Dashboards

1. **Grafana**: http://localhost:3000
   - Username: admin
   - Password: admin (change on first login)

2. **Prometheus**: http://localhost:9090

3. **Alertmanager**: http://localhost:9093

## Pre-configured Grafana Dashboards

### 1. Operations Dashboard (ops-dashboard.json)
Real-time operational metrics with 10s auto-refresh:
- Request rate by model and robot type
- Latency percentiles (p50, p95, p99)
- Error rate by status code
- GPU utilization and temperature
- Queue depth monitoring
- Worker utilization
- Top errors by type
- Success rate

**Use Case**: Real-time monitoring for on-call engineers and SREs

### 2. Business Dashboard (business-dashboard.json)
30-day business analytics:
- Daily inference counts by tier
- Revenue distribution
- Customer growth trends
- Usage by model
- Top 10 customers
- Quota utilization
- Monthly Recurring Revenue (MRR)
- Average Revenue Per User (ARPU)
- Churn rate

**Use Case**: Business analytics and growth tracking

### 3. Safety Dashboard (safety-dashboard.json)
7-day safety and compliance metrics:
- Safety incident counts by severity
- Violation type distribution
- Safety score trends
- Top violating customers
- Rejection rate over time
- Safety check latency
- Critical safety alerts
- Compliance score
- False positive rate

**Use Case**: Safety compliance monitoring and incident management

### 4. Customer Analytics Dashboard (customer-analytics-dashboard.json)
Per-customer insights with 30-day history:
- Usage patterns by robot type
- Instruction category distribution
- Success rate by robot
- Customer-specific latency
- Feedback rate
- Peak usage hours
- Total requests
- Quota utilization
- Error rate

**Use Case**: Customer success and support analysis

## Prometheus Alerts

### Alert Categories

#### Critical Alerts (immediate action required)
- **HighErrorRate**: Error rate > 5% for 5 minutes
- **GPUOverheating**: GPU temperature > 85°C for 2 minutes
- **SafetyIncidentSurge**: > 100 safety rejections/hour
- **CriticalSafetyIncident**: Any critical safety incident
- **ServiceDown**: API service health check failed
- **ModelInferenceFailure**: Model error rate > 2%

#### Warning Alerts (requires attention)
- **HighLatency**: p99 latency > 2s for 5 minutes
- **GPUMemoryHigh**: GPU memory > 95% for 5 minutes
- **HighQueueDepth**: > 80 pending requests for 5 minutes
- **HighValidationFailureRate**: Validation failures > 1%
- **QuotaExceeded**: Customer using > 95% of quota
- **WorkerOverloaded**: Worker utilization > 95%
- **RateLimitHitRate**: > 10 rate limit hits/second

## Configuration

### Update Alertmanager Notifications

Edit `/Users/aniksahai/Desktop/VLAAPI/monitoring/alertmanager/alertmanager.yml`:

```yaml
# Slack notifications
slack_configs:
  - api_url: 'YOUR_SLACK_WEBHOOK_URL'
    channel: '#your-channel'

# Email notifications
email_configs:
  - to: 'your-team@company.com'
    smarthost: 'smtp.gmail.com:587'
    auth_username: 'alerts@company.com'
    auth_password: 'your-password'

# PagerDuty notifications
pagerduty_configs:
  - service_key: 'YOUR_PAGERDUTY_KEY'
```

### Customize Alert Thresholds

Edit `/Users/aniksahai/Desktop/VLAAPI/monitoring/prometheus/alerts.yml`:

```yaml
- alert: HighErrorRate
  expr: rate(vla_inference_requests_total{status="error"}[5m]) > 0.05  # Change threshold
  for: 5m  # Change duration
```

### Add Custom Metrics

1. Add metric in your application:
```python
from prometheus_client import Counter, Histogram

custom_metric = Counter('vla_custom_metric_total', 'Description', ['label1', 'label2'])
custom_metric.labels(label1='value1', label2='value2').inc()
```

2. Create Prometheus query:
```promql
rate(vla_custom_metric_total[5m])
```

3. Add to Grafana dashboard

## Monitoring Best Practices

### Alert Fatigue Prevention
- Set appropriate thresholds to avoid false positives
- Use inhibition rules to suppress related alerts
- Implement escalation policies (warning → critical)
- Set reasonable repeat intervals

### Dashboard Organization
- **Operations**: Real-time (10s refresh) for incident response
- **Business**: Historical (5m refresh) for analysis
- **Safety**: Compliance-focused (1m refresh) for auditing
- **Customer**: Per-customer (5m refresh) for support

### Metric Retention
- **High-resolution**: 30 days (for debugging recent issues)
- **Downsampled**: 90+ days (for trend analysis)
- Use remote write for long-term storage if needed

### Performance Optimization
- Use recording rules for expensive queries
- Set appropriate scrape intervals
- Monitor Prometheus resource usage
- Use metric relabeling to drop unnecessary labels

## Troubleshooting

### Prometheus Not Scraping
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check scrape configs
docker exec vlaapi-prometheus cat /etc/prometheus/prometheus.yml

# View Prometheus logs
docker logs vlaapi-prometheus
```

### Grafana Dashboards Not Loading
```bash
# Check datasource connectivity
docker exec vlaapi-grafana curl http://prometheus:9090/-/healthy

# Verify provisioning
docker exec vlaapi-grafana ls /etc/grafana/provisioning/dashboards/

# View Grafana logs
docker logs vlaapi-grafana
```

### Alerts Not Firing
```bash
# Check alert rules
curl http://localhost:9090/api/v1/rules

# Verify Alertmanager connectivity
curl http://localhost:9093/-/healthy

# Check alert status
curl http://localhost:9093/api/v2/alerts

# View Alertmanager logs
docker logs vlaapi-alertmanager
```

### GPU Metrics Not Available
```bash
# Verify NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi

# Check DCGM exporter
docker logs vlaapi-dcgm-exporter

# Test GPU metrics endpoint
curl http://localhost:9400/metrics | grep dcgm
```

## Maintenance

### Backup Grafana Dashboards
```bash
# Export all dashboards
docker exec vlaapi-grafana grafana-cli admin export-dashboard > dashboards-backup.json
```

### Clean Up Old Metrics
```bash
# Prometheus automatically handles retention
# To manually trigger cleanup:
docker exec vlaapi-prometheus promtool tsdb cleanup /prometheus
```

### Update Alert Rules
```bash
# After editing alerts.yml
docker exec vlaapi-prometheus kill -HUP 1

# Or reload via API (if --web.enable-lifecycle is enabled)
curl -X POST http://localhost:9090/-/reload
```

## Security Considerations

1. **Change Default Credentials**
   - Grafana admin password
   - PostgreSQL database credentials
   - SMTP credentials in Alertmanager

2. **Network Security**
   - Use HTTPS in production
   - Restrict dashboard access via VPN or IP whitelist
   - Enable authentication for Prometheus/Alertmanager

3. **Secrets Management**
   - Store credentials in environment variables
   - Use Docker secrets for sensitive data
   - Never commit credentials to version control

4. **Access Control**
   - Implement role-based access in Grafana
   - Limit write access to Prometheus configuration
   - Audit alert rule changes

## Metrics Reference

### Core Metrics
- `vla_inference_requests_total{model, robot_type, status, tier}`
- `vla_inference_duration_seconds{model, robot_type}`
- `vla_inference_queue_depth`
- `vla_gpu_utilization_percent{gpu_id}`
- `vla_gpu_temperature_celsius{gpu_id}`
- `vla_gpu_memory_used_bytes{gpu_id}`
- `vla_safety_incidents_total{severity, violation_type}`
- `vla_safety_score`
- `vla_quota_used{customer_id, tier}`
- `vla_quota_limit{customer_id, tier}`

### Business Metrics
- `vla_revenue_total{tier}`
- `vla_customers_total`
- `vla_customers_active`
- `vla_customers_churned`
- `vla_mrr_total`

### System Metrics
- `vla_worker_active`
- `vla_worker_total`
- `vla_db_connections_active`
- `vla_db_connections_max`
- `vla_rate_limit_exceeded_total`

## Support

For issues or questions:
- Check Prometheus/Grafana official documentation
- Review runbook URLs in alert annotations
- Contact DevOps team for infrastructure issues
- Open GitHub issue for monitoring-related bugs
