# 🚀 Quick Launch Checklist

**Goal:** Get your VLA API accessible to users via your domain

---

## ✅ Pre-Launch Checklist (Do These First)

### 1. Get a Server
- [ ] Choose provider: AWS / GCP / Hetzner / Lambda Labs
- [ ] Minimum: 8 cores, 32GB RAM, GPU with 16GB+ VRAM
- [ ] Note the server's **public IP address**: `___.___.___.___`

### 2. Get a Domain
- [ ] Buy domain from Namecheap / Cloudflare / Google Domains
- [ ] Example: `myapi.com` or `mystartup.ai`
- [ ] Cost: ~$10-15/year

### 3. Point Domain to Server
**Option A: Cloudflare (Recommended - Free SSL)**
- [ ] Add domain to Cloudflare
- [ ] Change nameservers at registrar to Cloudflare's
- [ ] Create A record: `@` → Your server IP
- [ ] Create A record: `api` → Your server IP
- [ ] Enable "Full (Strict)" SSL mode
- [ ] Turn on "Always Use HTTPS"

**Option B: Direct DNS**
- [ ] In your registrar's DNS settings:
  - A record: `@` → Your server IP
  - A record: `api` → Your server IP
  - CNAME record: `www` → `@`

### 4. Setup Server
SSH into your server and run:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Install NGINX
sudo apt install nginx -y

# Install Certbot (for SSL)
sudo apt install certbot python3-certbot-nginx -y

# Install NVIDIA Docker (if you have GPU)
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

---

## 🚀 Launch Your API (Step-by-Step)

### Step 1: Upload Your Code to Server

**Option A: Git Clone**
```bash
cd /home/ubuntu
git clone https://github.com/yourusername/VLAAPI.git
cd VLAAPI
```

**Option B: Upload via SCP**
```bash
# On your local machine
scp -r /Users/aniksahai/Desktop/VLAAPI ubuntu@YOUR_SERVER_IP:/home/ubuntu/
```

### Step 2: Create Environment File

```bash
cd /home/ubuntu/VLAAPI

# Copy example env file
cat > .env << 'EOF'
# Application
APP_NAME="VLA Inference API"
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# API
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=https://api.yourdomain.com,https://yourdomain.com

# Database
DATABASE_URL=postgresql+asyncpg://vlaapi:CHANGE_THIS_PASSWORD@postgres:5432/vlaapi

# Redis
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY=GENERATE_WITH_openssl_rand_hex_32
API_KEY_ENCRYPTION_KEY=GENERATE_ANOTHER_ONE

# GPU
GPU_DEVICE=0
MODEL_DTYPE=bfloat16
USE_MOCK_MODELS=false

# Monitoring
ENABLE_PROMETHEUS=true
ENABLE_GPU_MONITORING=true
EOF

# Generate secure keys
echo "Your SECRET_KEY: $(openssl rand -hex 32)"
echo "Your API_KEY_ENCRYPTION_KEY: $(openssl rand -hex 32)"

# Edit .env and paste those keys
nano .env
```

**Replace:**
- `yourdomain.com` with your actual domain
- `CHANGE_THIS_PASSWORD` with a strong password
- Paste the generated secret keys

### Step 3: Start Docker Services

```bash
# Start production services
docker-compose --profile prod up -d

# Check if they're running
docker-compose ps

# Should see:
# - postgres (healthy)
# - redis (healthy)
# - api-prod (healthy)
# - prometheus (up)
# - grafana (up)

# View logs
docker-compose logs -f api-prod
```

If you see errors, check:
```bash
docker-compose logs postgres
docker-compose logs redis
```

### Step 4: Initialize Database

```bash
# Run database migrations
docker-compose exec api-prod alembic upgrade head

# Create first admin customer
docker-compose exec api-prod python scripts/create_customer.py \
  --email admin@yourdomain.com \
  --tier enterprise \
  --name "Admin User"

# Create API key (save this!)
docker-compose exec api-prod python scripts/create_customer.py \
  --create-api-key <CUSTOMER_ID_FROM_ABOVE> \
  --key-name "Admin Master Key"
```

**Save the API key!** You can't retrieve it again.

### Step 5: Configure NGINX

```bash
# Create NGINX config
sudo nano /etc/nginx/sites-available/vla-api
```

Paste this (replace `api.yourdomain.com`):

```nginx
# HTTP to HTTPS redirect
server {
    listen 80;
    server_name api.yourdomain.com;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    # SSL certificates (will be generated in next step)
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req zone=api_limit burst=20 nodelay;
    
    client_max_body_size 10M;
    
    # Proxy to FastAPI
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # WebSocket support
    location /v1/stream {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
    }
}
```

**If using Cloudflare SSL:**
Skip the SSL certificate lines, Cloudflare handles it.

```nginx
# Simplified for Cloudflare
server {
    listen 80;
    server_name api.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/vla-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Step 6: Setup SSL (If Not Using Cloudflare)

```bash
# Generate Let's Encrypt certificate
sudo certbot --nginx -d api.yourdomain.com

# Follow prompts
# - Enter email
# - Agree to terms
# - Choose: Redirect HTTP to HTTPS

# Test auto-renewal
sudo certbot renew --dry-run
```

### Step 7: Test Your API

```bash
# Test health endpoint
curl https://api.yourdomain.com/health

# Should return:
# {"status":"healthy", ...}

# Test inference endpoint (use your API key)
curl -X POST https://api.yourdomain.com/v1/inference \
  -H "Authorization: Bearer YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "base64_encoded_image_here",
    "instruction": "pick up the red block",
    "robot_id": "test-robot-001"
  }'
```

If it works: **🎉 Your API is live!**

### Step 8: Setup Firewall

```bash
# Enable UFW firewall
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable

# Check status
sudo ufw status
```

### Step 9: Setup Monitoring Access

Access Grafana dashboard:
- URL: `http://YOUR_SERVER_IP:3000`
- Username: `admin`
- Password: `admin` (change this!)

**Important:** Don't expose Grafana publicly! Either:
1. Access via SSH tunnel: `ssh -L 3000:localhost:3000 ubuntu@YOUR_SERVER_IP`
2. Add NGINX auth
3. Restrict to your IP in firewall

---

## 📝 Post-Launch Tasks

### Immediate (Day 1)
- [ ] Test API with your admin API key
- [ ] Check Grafana dashboards are working
- [ ] Setup automated backups (database, .env file)
- [ ] Save all credentials securely (password manager)
- [ ] Change default Grafana password
- [ ] Create monitoring alerts (disk space, errors)

### This Week
- [ ] Write basic API documentation
  - What endpoints exist
  - How to authenticate
  - Example requests
  - Error codes
- [ ] Create simple landing page
  - What your API does
  - "Contact for access" form
  - Link to docs
- [ ] Setup error tracking (optional: Sentry.io free tier)
- [ ] Create backup script

### This Month
- [ ] Build user dashboard (see PRODUCTION_DEPLOYMENT_GUIDE.md)
- [ ] Setup payment integration (Stripe)
- [ ] Create email automation (SendGrid)
- [ ] Add more documentation
- [ ] Onboard first beta users

---

## 🆘 Troubleshooting

### API not accessible at domain

**Check DNS propagation:**
```bash
dig api.yourdomain.com
# Should return your server IP
```

**Check NGINX:**
```bash
sudo nginx -t
sudo systemctl status nginx
sudo tail -f /var/log/nginx/error.log
```

**Check Docker:**
```bash
docker-compose ps
docker-compose logs api-prod
```

### SSL certificate errors

**If using Let's Encrypt:**
```bash
sudo certbot certificates
sudo certbot renew
```

**If using Cloudflare:**
- Check SSL mode is "Full (Strict)"
- Verify nameservers point to Cloudflare
- Wait 5-10 minutes for DNS propagation

### Database connection errors

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Connect manually
docker-compose exec postgres psql -U vlaapi -d vlaapi
```

### GPU not detected

```bash
# Check NVIDIA driver
nvidia-smi

# Check Docker can access GPU
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# Check your container
docker-compose exec api-prod nvidia-smi
```

### Out of memory

```bash
# Check system resources
htop
df -h

# Check Docker stats
docker stats

# Restart services
docker-compose restart api-prod
```

---

## 📞 Need Help?

### Common Issues
1. **502 Bad Gateway** → FastAPI not running (check `docker-compose ps`)
2. **504 Gateway Timeout** → Request took too long (increase timeout)
3. **401 Unauthorized** → Invalid API key
4. **429 Too Many Requests** → Rate limit hit
5. **500 Internal Server Error** → Check logs (`docker-compose logs`)

### Useful Commands

```bash
# View all logs
docker-compose logs -f

# Restart API
docker-compose restart api-prod

# Rebuild after code changes
docker-compose build api-prod
docker-compose up -d api-prod

# Check disk space
df -h

# Check memory
free -h

# Check processes
htop

# Database backup
docker-compose exec postgres pg_dump -U vlaapi vlaapi > backup.sql

# Restore database
docker-compose exec -T postgres psql -U vlaapi vlaapi < backup.sql
```

### Log Locations
- **API logs**: `docker-compose logs api-prod`
- **NGINX logs**: `/var/log/nginx/access.log` and `error.log`
- **PostgreSQL logs**: `docker-compose logs postgres`
- **System logs**: `sudo journalctl -u nginx` or `dmesg`

---

## 🎯 You're Live When...

- [ ] `curl https://api.yourdomain.com/health` returns 200 OK
- [ ] You can make an inference request with your API key
- [ ] SSL shows a green lock in browser
- [ ] Grafana shows metrics
- [ ] Database has your admin customer

**Congratulations! Your API is production-ready! 🚀**

---

## What's Next?

See `PRODUCTION_DEPLOYMENT_GUIDE.md` for:
- Building a user dashboard
- Adding payment integration
- Creating documentation portal
- Setting up admin tools
- Scaling to 1000+ users

**For now, you have:**
✅ Working API accessible via your domain  
✅ SSL/HTTPS encryption  
✅ Database + Redis + Monitoring  
✅ GPU inference working  
✅ Can manually onboard users

**You're missing:**
❌ User signup/login UI  
❌ Dashboard for users  
❌ Payment system  
❌ Public documentation

**MVP is live!** Build the dashboard when you have first users interested.






