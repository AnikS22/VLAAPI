# 🎓 FAU Computer Deployment - Complete Guide

**Deploy VLA API from your Mac at home to FAU computer with Titan X GPUs**

---

## ✅ What Just Happened

Your code is now on GitHub at: **https://github.com/AnikS22/VLAAPI**

✅ All VLA API code committed  
✅ All Claude-Flow files excluded  
✅ Clean, production-ready repository  
✅ Ready to clone on FAU computer  

---

## 🚀 Complete Deployment Steps

### Step 1: Get FAU VPN Access (If you don't have it)

**Contact FAU IT:**
- **Email:** it@fau.edu  
- **Phone:** (561) 297-3999  
- **Request:** "VPN access to connect to my research computer remotely"

They'll give you:
- VPN client (usually Cisco AnyConnect)
- VPN credentials
- Instructions

---

### Step 2: Connect to FAU VPN

**On your Mac at home:**

1. Open Cisco AnyConnect (or FAU's VPN client)
2. Enter VPN server address (from FAU IT)
3. Login with your FAU credentials
4. Connect

**You're now "virtually" on FAU's network!**

---

### Step 3: Find Your FAU Computer's IP

**Option A: If you know it already**
- Use the IP address you have

**Option B: Ask your lab administrator**
- They should know the computer's IP

**Option C: If you can physically access it**
```bash
# On the FAU computer, run:
hostname -I
# Example output: 10.192.45.123
```

---

### Step 4: Clone Repository on FAU Computer

**From your Mac (connected to FAU VPN):**

```bash
# SSH into FAU computer
ssh your-fau-username@fau-computer-ip

# Example:
# ssh asahai@10.192.45.123
```

**Once logged into FAU computer:**

```bash
# Clone your GitHub repository
git clone https://github.com/AnikS22/VLAAPI.git

# Navigate to it
cd VLAAPI

# Verify it's there
ls -la
```

**That's it!** Your code is now on the FAU computer.

---

### Step 5: Deploy on FAU Computer

**Still on FAU computer via SSH:**

```bash
cd ~/VLAAPI

# Make scripts executable
chmod +x scripts/*.sh

# Run deployment (takes 10-15 minutes)
./scripts/remote_gpu_deploy.sh
```

**What it does:**
- ✅ Checks for NVIDIA GPU (your Titan X)
- ✅ Installs Docker if needed
- ✅ Installs NVIDIA Container Toolkit
- ✅ Downloads VLA models (~16GB)
- ✅ Starts PostgreSQL, Redis, API, Prometheus, Grafana
- ✅ Creates test customer and API key

**IMPORTANT:** At the end, it will print an API key like:
```
API_KEY=vla_remote_abc123def456...
```

**SAVE THIS KEY!** You'll need it for testing.

---

### Step 6: Test from Your Mac

**Back on your Mac (still connected to FAU VPN):**

```bash
# Set your FAU computer's IP and API key
export FAU_IP="10.192.45.123"  # Use your actual IP
export API_KEY="vla_remote_abc123..."  # Use your actual key

# Test health
curl http://$FAU_IP:8000/health

# Expected: {"status":"healthy"}

# Test real GPU inference!
curl -X POST http://$FAU_IP:8000/v1/inference \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openvla-7b",
    "image": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    "instruction": "pick up the red cube",
    "robot_config": {"type": "franka_panda"}
  }' | jq

# Should return real robot action!
```

---

### Step 7: View Dashboards

**Open in your browser (connected to FAU VPN):**

- **Grafana:** http://fau-ip:3000 (login: admin/admin123)
- **Prometheus:** http://fau-ip:9090
- **API Docs:** http://fau-ip:8000/docs

**You'll see:**
- Real-time GPU metrics
- Request rates
- Inference latency (~120-150ms with Titan X)
- System health

---

## 🎯 Your Complete Workflow

```
┌───────────────────────────────────────────────────┐
│  YOUR MAC (at home)                               │
│                                                    │
│  1. Connect to FAU VPN                            │
│  2. SSH to FAU computer                           │
│  3. Git clone the repo                            │
│  4. Run deployment script                         │
│  5. Test API from your Mac                        │
│  6. View dashboards in browser                    │
└───────────────────────────────────────────────────┘
```

---

## 📊 What You Can Do

### From Your Mac at Home:

✅ **Make API calls** to FAU computer  
✅ **View Grafana dashboards** (GPU metrics, latency, etc.)  
✅ **Check API documentation** (interactive Swagger UI)  
✅ **Query database** (via psql through SSH)  
✅ **View logs** (via Docker commands through SSH)  

### Example: Python Client on Your Mac

```python
#!/usr/bin/env python3
"""Test FAU GPU API from your Mac."""

import requests

FAU_IP = "10.192.45.123"  # Your FAU computer
API_KEY = "vla_remote_abc123..."  # From deployment

response = requests.post(
    f"http://{FAU_IP}:8000/v1/inference",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={
        "model": "openvla-7b",
        "image": "BASE64_IMAGE_HERE",
        "instruction": "pick up the red cube"
    }
)

action = response.json()["action"]["values"]
print(f"Robot action: {action}")
```

---

## 🔍 Checking GPU Usage

**SSH to FAU computer:**

```bash
ssh user@fau-computer-ip

# Watch GPU in real-time
watch -n 1 nvidia-smi

# Check API logs
docker logs -f vlaapi-api-remote | grep "inference_ms"

# Check GPU metrics via API
curl http://localhost:8000/monitoring/gpu/stats | jq
```

**You should see:**
- GPU Memory: ~8-10GB used (OpenVLA-7B loaded)
- GPU Utilization: Spikes to 60-80% during inference
- Temperature: Should stay below 80°C

---

## 🐛 Troubleshooting

### Can't SSH to FAU Computer

**Problem:** `ssh: connect to host X.X.X.X port 22: Connection refused`

**Solutions:**
1. Make sure you're connected to FAU VPN
2. Check IP address is correct
3. Contact FAU IT if SSH not enabled

### Can't Access API from Mac

**Problem:** `curl: (7) Failed to connect`

**Solutions:**
```bash
# On FAU computer, check firewall
sudo ufw status
sudo ufw allow 8000/tcp  # Allow API port

# Or temporarily disable for testing
sudo ufw disable
```

### GPU Not Being Used

**Problem:** Slow inference times (>500ms)

**Solutions:**
```bash
# SSH to FAU computer
ssh user@fau-ip

# Check GPU is detected
nvidia-smi

# Check Docker can access GPU
docker exec vlaapi-api-remote nvidia-smi

# Check API logs
docker logs vlaapi-api-remote | grep -i gpu
```

---

## 📝 Important Information

### Repository
- **URL:** https://github.com/AnikS22/VLAAPI
- **Branch:** main
- **Files:** 3,185 (all VLA API, no Claude-Flow)

### API Keys
- Generated by deployment script
- Stored in: `remote_api_key.txt` on FAU computer
- **Save it!** You can't retrieve it later

### Ports Used
- **8000** - API server
- **5432** - PostgreSQL
- **6379** - Redis
- **3000** - Grafana dashboards
- **9090** - Prometheus metrics

### Data Storage
- **Database:** Docker volume (persists)
- **Models:** Docker volume (~16GB)
- **Logs:** Docker container logs

---

## ✅ Success Checklist

- [ ] FAU VPN access obtained
- [ ] Can SSH to FAU computer
- [ ] Repository cloned on FAU computer
- [ ] Deployment script ran successfully
- [ ] API key saved
- [ ] Can access API from Mac (via VPN)
- [ ] Can view Grafana dashboard
- [ ] GPU detected and being used

**All ✅ → You're running real GPU inference from home!** 🎉

---

## 🔄 Common Commands

```bash
# On FAU computer (via SSH):
cd ~/VLAAPI

# View running services
docker ps

# View API logs
docker logs -f vlaapi-api-remote

# Restart API
docker-compose -f docker-compose.remote.yml restart api

# Stop everything
docker-compose -f docker-compose.remote.yml down

# Start everything
docker-compose -f docker-compose.remote.yml up -d

# View GPU usage
nvidia-smi

# Check database
docker exec -it vlaapi-postgres-remote psql -U vlaapi -d vlaapi
```

---

## 💰 Costs

**Running on FAU computer:**
- ✅ **Free!** (FAU provides electricity and hardware)
- ✅ No cloud costs
- ✅ Full GPU access

---

## 📚 Next Steps

### After Testing Works:

1. **Test with real images**
   - Send actual robot camera images
   - Test different instructions
   - Verify action quality

2. **Monitor performance**
   - Watch Grafana dashboards
   - Check GPU utilization
   - Review latency metrics

3. **Scale if needed**
   - Use both Titan X GPUs
   - Add more workers
   - Tune configuration

4. **Production deployment**
   - Follow [docs/DEPLOYMENT_AND_OPERATIONS.md](docs/DEPLOYMENT_AND_OPERATIONS.md)
   - Add SSL certificates
   - Set up proper monitoring

---

## 🎯 Summary

**Your exact steps:**

```bash
# 1. On your Mac - Connect VPN
# 2. On your Mac - SSH to FAU
ssh your-username@fau-computer-ip

# 3. On FAU computer - Clone repo
git clone https://github.com/AnikS22/VLAAPI.git
cd VLAAPI

# 4. On FAU computer - Deploy
./scripts/remote_gpu_deploy.sh
# Save the API key!

# 5. On your Mac - Test
curl http://fau-ip:8000/health
```

**That's it!** 🚀

---

## 📞 Support

**Need help?**
- Check troubleshooting section above
- Read: [docs/REMOTE_ACCESS_SETUP.md](docs/REMOTE_ACCESS_SETUP.md)
- Contact FAU IT for network issues

---

**Repository:** https://github.com/AnikS22/VLAAPI  
**Status:** ✅ Ready to deploy!  
**Next Step:** Connect to FAU VPN and follow Step 2! 🎓

