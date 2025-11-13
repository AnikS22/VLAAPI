# Praxis Labs - Deployment Guide

## 🚀 Production Deployment Checklist

### Prerequisites

- [ ] PostgreSQL 15+ database
- [ ] Redis instance
- [ ] Stripe account (for billing)
- [ ] GPU instance (for VLA models) - Optional for MVP
- [ ] Domain name configured
- [ ] SSL certificates

---

## Backend Deployment

### 1. Environment Setup

Create `.env` file in project root:

```bash
# Application
APP_NAME="Praxis Labs VLA API"
APP_VERSION="1.0.0"
ENVIRONMENT="production"
DEBUG=false

# API Server
API_HOST="0.0.0.0"
API_PORT=8000

# Database
DATABASE_URL="postgresql+asyncpg://user:password@host:5432/vlaapi"

# Redis
REDIS_URL="redis://localhost:6379/0"

# JWT Authentication
JWT_SECRET_KEY="your-super-secret-key-min-32-chars"
JWT_ALGORITHM="HS256"
JWT_EXPIRATION_MINUTES=30

# Stripe
STRIPE_SECRET_KEY="sk_live_..."
STRIPE_PUBLISHABLE_KEY="pk_live_..."
STRIPE_WEBHOOK_SECRET="whsec_..."
STRIPE_PRICE_ID_PRO="price_..."
STRIPE_PRICE_ID_ENTERPRISE="price_..."

# CORS
CORS_ORIGINS="https://app.praxislabs.com,https://praxislabs.com"

# Feature Flags
ENABLE_GPU_MONITORING=true
ENABLE_PROMETHEUS=true
ENABLE_EMBEDDINGS=false  # Set true when ready
```

### 2. Database Migration

```bash
# Create database
createdb vlaapi

# Run migrations
psql -d vlaapi < migrations/001_create_users_and_auth.sql

# Create admin user
psql -d vlaapi << EOF
INSERT INTO vlaapi.users (email, hashed_password, full_name, is_superuser, is_active, email_verified)
VALUES (
    'admin@praxislabs.com',
    '\$2b\$12\$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5ND0azvKJMJtu',
    'Admin User',
    true,
    true,
    true
);
EOF
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run with Gunicorn + Uvicorn

```bash
gunicorn src.api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log \
  --log-level info
```

### 5. Systemd Service (Recommended)

Create `/etc/systemd/system/praxis-api.service`:

```ini
[Unit]
Description=Praxis Labs VLA API
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=praxis
Group=praxis
WorkingDirectory=/opt/praxis-labs
Environment="PATH=/opt/praxis-labs/venv/bin"
ExecStart=/opt/praxis-labs/venv/bin/gunicorn src.api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable praxis-api
sudo systemctl start praxis-api
sudo systemctl status praxis-api
```

---

## Frontend Deployment (Vercel)

### 1. Environment Variables

In Vercel dashboard, add:

```
NEXT_PUBLIC_API_URL=https://api.praxislabs.com
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...
```

### 2. Deploy

```bash
cd frontend

# Install Vercel CLI
npm install -g vercel

# Deploy
vercel --prod
```

Or connect GitHub repo to Vercel for automatic deployments.

### 3. Custom Domain

In Vercel dashboard:
- Add custom domain: `app.praxislabs.com`
- Configure DNS records
- Enable automatic HTTPS

---

## Nginx Configuration

### Backend Proxy

```nginx
server {
    listen 443 ssl http2;
    server_name api.praxislabs.com;

    ssl_certificate /etc/letsencrypt/live/api.praxislabs.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.praxislabs.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts for long inference requests
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
    limit_req zone=api burst=20 nodelay;
}
```

---

## Database Backup

### Automated Daily Backups

Create `/opt/praxis-labs/scripts/backup.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/opt/praxis-labs/backups"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="vlaapi_backup_${DATE}.sql.gz"

# Create backup
pg_dump vlaapi | gzip > "${BACKUP_DIR}/${FILENAME}"

# Keep only last 30 days
find ${BACKUP_DIR} -name "vlaapi_backup_*.sql.gz" -mtime +30 -delete

# Upload to S3 (optional)
# aws s3 cp "${BACKUP_DIR}/${FILENAME}" s3://praxis-backups/database/
```

Add to crontab:

```
0 2 * * * /opt/praxis-labs/scripts/backup.sh
```

---

## Monitoring Setup

### Prometheus

`prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'praxis-api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Grafana Dashboards

Import these dashboards:
- Node Exporter Full
- PostgreSQL Database
- FastAPI Application Metrics

### Alerting

Configure alerts for:
- High error rate (>5%)
- Low success rate (<90%)
- High latency (>5s p99)
- Critical safety incidents
- Database connection failures

---

## Stripe Webhook Configuration

### 1. Create Webhook in Stripe Dashboard

URL: `https://api.praxislabs.com/v1/billing/webhooks/stripe`

Events to subscribe:
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.payment_succeeded`
- `invoice.payment_failed`

### 2. Add Webhook Secret to .env

```bash
STRIPE_WEBHOOK_SECRET=whsec_...
```

---

## Security Hardening

### 1. Firewall Rules

```bash
# Allow SSH, HTTP, HTTPS
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp

# Block direct access to API port
ufw deny 8000/tcp

# Enable firewall
ufw enable
```

### 2. PostgreSQL Security

```sql
-- Restrict network access
-- Edit postgresql.conf:
listen_addresses = 'localhost'

-- Edit pg_hba.conf:
host    vlaapi    vlaapi_user    127.0.0.1/32    scram-sha-256
```

### 3. API Rate Limiting

Already implemented in code:
- Free tier: 100 requests/day
- Pro tier: 50,000 requests/month
- Enforced per API key

### 4. SSL/TLS

Use Let's Encrypt with auto-renewal:

```bash
certbot --nginx -d api.praxislabs.com
certbot --nginx -d app.praxislabs.com

# Auto-renewal cron
0 0 * * * certbot renew --quiet
```

---

## Health Checks

### API Health Endpoint

```bash
curl https://api.praxislabs.com/
```

Expected response:

```json
{
  "name": "Praxis Labs VLA API",
  "version": "1.0.0",
  "status": "running"
}
```

### Database Health

```bash
psql -d vlaapi -c "SELECT 1"
```

### Redis Health

```bash
redis-cli ping
```

---

## Scaling Considerations

### Horizontal Scaling

1. **Load Balancer**: Use nginx or AWS ALB
2. **Multiple API Instances**: Run on different servers
3. **Shared Database**: All instances connect to same PostgreSQL
4. **Shared Redis**: Use Redis cluster or AWS ElastiCache
5. **Session Persistence**: JWT tokens are stateless (no sticky sessions needed)

### Database Optimization

```sql
-- Add indexes for common queries
CREATE INDEX CONCURRENTLY idx_inference_logs_customer_timestamp
ON vlaapi.inference_logs(customer_id, timestamp DESC);

CREATE INDEX CONCURRENTLY idx_safety_incidents_severity_timestamp
ON vlaapi.safety_incidents(severity, timestamp DESC);

-- Partition inference_logs by month
CREATE TABLE vlaapi.inference_logs_2024_01
PARTITION OF vlaapi.inference_logs
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

### Caching Strategy

- API key validation: 10 minutes (Redis)
- Consent preferences: 10 minutes (Redis)
- Analytics aggregations: 5 minutes (Redis)
- Customer tier info: 1 hour (Redis)

---

## Disaster Recovery

### Backup Restoration

```bash
# Stop API
sudo systemctl stop praxis-api

# Restore database
gunzip -c backup.sql.gz | psql vlaapi

# Restart API
sudo systemctl start praxis-api
```

### Rollback Plan

1. Keep previous 5 deployments
2. Tag releases in Git
3. Blue-green deployment recommended
4. Database migrations versioned and reversible

---

## Cost Estimation

### Monthly Costs (Estimated)

**Infrastructure**:
- DigitalOcean Droplet (4GB RAM): $24/month
- PostgreSQL Managed Database: $15/month
- Redis Managed: $10/month
- **Total**: ~$50/month

**Alternative (GPU for VLA)**:
- AWS g4dn.xlarge (GPU): ~$350/month
- RDS PostgreSQL: ~$50/month
- ElastiCache Redis: ~$30/month
- **Total**: ~$430/month

**Additional**:
- Domain: $12/year
- SSL: Free (Let's Encrypt)
- Stripe: 2.9% + $0.30 per transaction
- S3 backups: ~$5/month

---

## Launch Checklist

- [ ] Backend deployed and running
- [ ] Frontend deployed on Vercel
- [ ] Database migrated
- [ ] Admin user created
- [ ] Stripe configured
- [ ] Webhooks tested
- [ ] SSL certificates active
- [ ] Monitoring configured
- [ ] Backups scheduled
- [ ] Load testing completed
- [ ] Security audit performed
- [ ] Documentation updated
- [ ] Support email configured
- [ ] Terms of Service published
- [ ] Privacy Policy published

---

## Post-Launch

### Week 1
- Monitor error rates
- Check Stripe payments
- Review user feedback
- Fix critical bugs

### Month 1
- Analyze usage patterns
- Optimize slow queries
- Add requested features
- Scale as needed

### Ongoing
- Weekly backups verification
- Monthly security updates
- Quarterly penetration testing
- Annual disaster recovery drill

---

## Support

**Documentation**: https://docs.praxislabs.com
**Status Page**: https://status.praxislabs.com
**Support Email**: support@praxislabs.com

---

**Last Updated**: 2025-11-06
**Version**: 1.0.0
