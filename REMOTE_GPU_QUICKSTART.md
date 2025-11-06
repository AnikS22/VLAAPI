# 🎮 Remote GPU Testing - Quick Start

**Deploy to your Linux PC with Titan X GPUs in 3 steps!**

---

## Your Setup

✅ **Remote Linux PC** with dual Titan X GPUs  
✅ **SSH access** from your Mac  
✅ **Goal:** Run real VLA inference with GPU acceleration  

---

## 🚀 3-Step Deployment

### Step 1: Copy Project to Server

**From your Mac:**

```bash
# Copy entire project to your remote server
rsync -avz --exclude 'node_modules' --exclude 'venv' --exclude '.git' \
  /Users/aniksahai/Desktop/VLAAPI/ \
  user@your-server-ip:~/VLAAPI/
```

### Step 2: Run Deployment Script

**SSH into your server:**

```bash
ssh user@your-server-ip
cd ~/VLAAPI
./scripts/remote_gpu_deploy.sh
```

This script will:
- ✅ Check for NVIDIA GPU (your Titan X)
- ✅ Install Docker if needed
- ✅ Install NVIDIA Container Toolkit
- ✅ Download VLA model (~16GB, first time only)
- ✅ Start all services with GPU support
- ✅ Create test customer and API key
- ✅ Takes 10-15 minutes

### Step 3: Test from Your Mac

**The script creates a test file for you:**

```bash
# Still on the server, copy the test script
cat test_remote_from_mac.sh

# OR use the API key directly
cat remote_api_key.txt
```

**Then on your Mac:**

```bash
# Set these (from the deployment output)
export SERVER_IP="your-server-ip"
export API_KEY="vla_remote_abc123..."

# Test health
curl http://$SERVER_IP:8000/health

# Test real GPU inference!
curl -X POST http://$SERVER_IP:8000/v1/inference \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openvla-7b",
    "image": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    "instruction": "pick up the red cube"
  }' | jq
```

**Expected response:**
```json
{
  "action": {
    "values": [0.15, -0.08, 0.22, 0.01, 0.05, -0.03, 1.0]
  },
  "performance": {
    "inference_ms": 125  ← Real GPU inference!
  }
}
```

---

## 📊 View Dashboards

Open in your browser (replace with your server IP):

- **Grafana:** http://your-server-ip:3000 (admin/admin123)
- **Prometheus:** http://your-server-ip:9090
- **API Docs:** http://your-server-ip:8000/docs

You'll see:
- Real-time GPU metrics
- Inference latency (~120-150ms with GPU)
- GPU memory usage
- Request rates

---

## 🔍 Check GPU Usage

**On your server:**

```bash
# Watch GPU in real-time
watch -n 1 nvidia-smi

# Check API logs
docker logs -f vlaapi-api-remote | grep "inference_ms"

# View GPU metrics
curl http://localhost:8000/monitoring/gpu/stats | jq
```

You should see:
- GPU Memory: ~8-10GB used (OpenVLA-7B model)
- GPU Utilization: Spikes to 60-80% during inference
- Temperature: Should stay below 80°C

---

## 💡 Differences from Local Deployment

| Feature | Local (Mock) | Remote (GPU) |
|---------|-------------|--------------|
| **Models** | Mock (instant) | Real VLA (~16GB) |
| **GPU** | Not used | Titan X used! |
| **Inference Time** | ~50ms (fake) | ~125ms (real) |
| **First Start** | 30 seconds | 10-15 minutes |
| **Results** | Random actions | Real AI predictions |
| **Use Case** | Testing workflows | Real testing |

---

## ⚙️ Configuration

### Use Second GPU

Edit on server: `.env.remote`

```bash
GPU_DEVICE=1  # Switch to second Titan X
```

Restart:
```bash
docker-compose -f docker-compose.remote.yml restart api
```

### Adjust Workers

For better performance:

```bash
# Edit .env.remote
INFERENCE_MAX_WORKERS=2  # Use 2 concurrent workers

# Restart
docker-compose -f docker-compose.remote.yml restart api
```

---

## 🐛 Troubleshooting

### Can't Connect from Mac

```bash
# On server, check firewall
sudo ufw allow 8000/tcp
sudo ufw allow 3000/tcp

# Or temporarily disable for testing
sudo ufw disable
```

### GPU Not Being Used

```bash
# Check container can see GPU
docker exec vlaapi-api-remote nvidia-smi

# Check logs for GPU initialization
docker logs vlaapi-api-remote | grep -i gpu
```

### Out of Memory

```bash
# Edit .env.remote on server
MODEL_DTYPE=float16  # Use half precision (saves memory)
INFERENCE_BATCH_SIZE=1  # Process one at a time

# Restart
docker-compose -f docker-compose.remote.yml restart api
```

---

## 📈 Performance Expectations

With Titan X GPU:

| Metric | Expected |
|--------|----------|
| **Model Loading** | 5-10 minutes (first time) |
| **Inference Latency** | 120-150ms |
| **Throughput** | 6-8 requests/second |
| **GPU Memory** | 8-10GB / 12GB |
| **GPU Utilization** | 60-80% during inference |

**This is 8-10x faster than CPU!**

---

## 🔄 Common Commands

```bash
# SSH to server
ssh user@your-server-ip
cd ~/VLAAPI

# View all services
docker ps

# View API logs
docker logs -f vlaapi-api-remote

# View GPU usage
nvidia-smi

# Restart API
docker-compose -f docker-compose.remote.yml restart api

# Stop everything
docker-compose -f docker-compose.remote.yml down

# Restart everything
./scripts/remote_gpu_deploy.sh
```

---

## ✅ Success Checklist

- [ ] Script completed without errors
- [ ] `docker ps` shows 5 running containers
- [ ] `nvidia-smi` shows GPU memory used (~8-10GB)
- [ ] Can access API from Mac
- [ ] Inference returns real results in ~125ms
- [ ] Grafana shows GPU metrics
- [ ] Temperature stays below 80°C

**All ✅ → Your GPU deployment works!** 🎉

---

## 🔄 Comparison Table

### Local vs Remote Deployment

|  | **Local Mock** | **Remote GPU** |
|--|----------------|----------------|
| **Location** | Your Mac | Linux server |
| **Hardware** | Any CPU | Titan X GPU |
| **Models** | Mock | Real VLA-7B |
| **Inference** | Instant (fake) | 125ms (real) |
| **Use For** | Testing workflows | Real testing |
| **Setup Time** | 5 minutes | 15 minutes |
| **Cost** | Free (local) | Server costs |

### When to Use Each

- **Local Mock:** Test API structure, customer flows, dashboards
- **Remote GPU:** Test real inference, performance, GPU optimization

---

## 📚 Full Documentation

- **This guide:** Quick start (you are here)
- **Complete guide:** `docs/REMOTE_GPU_DEPLOYMENT.md`
- **Local testing:** `LOCAL_DEPLOYMENT_QUICKSTART.md`
- **Production:** `docs/DEPLOYMENT_AND_OPERATIONS.md`

---

## 🎯 Next Steps

### After Testing Works

1. **Optimize performance**
   - Tune worker count
   - Try batch processing
   - Monitor GPU utilization

2. **Test with real images**
   - Send actual robot camera images
   - Test different instructions
   - Verify action quality

3. **Load testing**
   - Simulate multiple customers
   - Test concurrent requests
   - Find throughput limits

4. **Production planning**
   - Document what works
   - Plan scaling strategy
   - Follow production deployment guide

---

## 💰 Cost Estimate

Running on your own hardware:
- **Electricity:** ~$0.50-1.00/day (250W GPU)
- **No cloud costs!** ✅
- **Full control** over hardware

---

## 🎉 Summary

**You have:**
- ✅ Real VLA models running
- ✅ GPU acceleration (8-10x faster)
- ✅ Complete API stack
- ✅ Monitoring dashboards
- ✅ Test customer accounts

**Next:**
- Test from your Mac
- View dashboards
- Monitor GPU performance
- Prepare for production!

---

**Questions?** See `docs/REMOTE_GPU_DEPLOYMENT.md` for detailed explanations.

**Ready to deploy?** Just run: `./scripts/remote_gpu_deploy.sh` 🚀

