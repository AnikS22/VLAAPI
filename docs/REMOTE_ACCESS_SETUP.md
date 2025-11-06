# 🌐 Remote Access Setup - Testing from Home

**Connect to your FAU computer from home and test the API**

---

## 🎯 Your Situation

- **Computer 1:** Mac at home (where you are now)
- **Computer 2:** Linux PC at FAU with Titan X GPUs (on FAU wifi)
- **Goal:** Deploy API on FAU computer, test from your Mac at home

---

## 🚀 Complete Setup Guide

### Step 1: Get Access to FAU Computer

You have **3 options** depending on FAU's network setup:

#### **Option A: Direct SSH (If FAU allows)**

If FAU computer has a public IP or you have VPN access:

```bash
# From your Mac at home
ssh your-username@fau-computer-ip

# Example
ssh asahai@134.68.xxx.xxx
```

**How to find FAU computer's IP:**
```bash
# On the FAU computer, run:
curl ifconfig.me

# Or
hostname -I
```

#### **Option B: SSH via FAU VPN (Most Common)**

Most universities require VPN for external access:

1. **Install FAU VPN client** on your Mac
   - Contact FAU IT for VPN instructions
   - Usually Cisco AnyConnect or similar

2. **Connect to FAU VPN** from home

3. **Then SSH** to the internal FAU computer IP:
```bash
# Connect VPN first, then:
ssh your-username@10.x.x.x  # Internal IP
```

#### **Option C: SSH Tunnel/Port Forwarding (If allowed)**

If you already have SSH access to FAU, create a tunnel:

```bash
# From your Mac
ssh -L 8000:localhost:8000 your-username@fau-computer
```

This forwards FAU computer's port 8000 to your Mac's localhost:8000.

---

### Step 2: Install Code on FAU Computer

You have **2 methods:**

#### **Method 1: Clone from GitHub (Recommended if you have a repo)**

```bash
# 1. SSH into FAU computer
ssh your-username@fau-computer

# 2. Clone the repository
git clone https://github.com/yourusername/VLAAPI.git
cd VLAAPI

# Done! Code is now on FAU computer
```

#### **Method 2: Copy from Your Mac (If no GitHub repo)**

**Option 2a: Using rsync (Recommended)**
```bash
# From your Mac at home (while connected to FAU VPN)
rsync -avz --progress \
  --exclude 'node_modules' \
  --exclude 'venv' \
  --exclude '.git' \
  --exclude '__pycache__' \
  /Users/aniksahai/Desktop/VLAAPI/ \
  your-username@fau-computer:~/VLAAPI/

# Example:
rsync -avz --progress \
  --exclude 'node_modules' \
  /Users/aniksahai/Desktop/VLAAPI/ \
  asahai@134.68.xxx.xxx:~/VLAAPI/
```

**Option 2b: Using scp**
```bash
# From your Mac (simpler but slower)
cd /Users/aniksahai/Desktop
tar -czf VLAAPI.tar.gz VLAAPI/
scp VLAAPI.tar.gz your-username@fau-computer:~/

# Then on FAU computer:
ssh your-username@fau-computer
tar -xzf VLAAPI.tar.gz
cd VLAAPI
```

**Option 2c: Using Git (Create repo first)**
```bash
# On your Mac, create a repo
cd /Users/aniksahai/Desktop/VLAAPI
git init
git add .
git commit -m "Initial commit"

# Push to GitHub (or GitLab/Bitbucket)
git remote add origin https://github.com/yourusername/VLAAPI.git
git push -u origin main

# Then clone on FAU computer
ssh your-username@fau-computer
git clone https://github.com/yourusername/VLAAPI.git
```

---

### Step 3: Deploy on FAU Computer

Once code is on FAU computer:

```bash
# SSH into FAU computer
ssh your-username@fau-computer

# Navigate to project
cd ~/VLAAPI

# Run deployment script
chmod +x scripts/remote_gpu_deploy.sh
./scripts/remote_gpu_deploy.sh
```

**Wait 10-15 minutes** for it to:
- Install Docker (if needed)
- Download VLA models (~16GB)
- Start all services
- Create test API key

**Save the API key** that gets printed!

---

### Step 4: Test from Your Mac at Home

#### **Scenario A: You're on FAU VPN**

If connected to FAU VPN, you can access directly:

```bash
# From your Mac (connected to FAU VPN)
# Replace with FAU computer's internal IP
export FAU_IP="10.x.x.x"
export API_KEY="vla_remote_abc123..."

# Test health
curl http://$FAU_IP:8000/health

# Test inference
curl -X POST http://$FAU_IP:8000/v1/inference \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openvla-7b",
    "image": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    "instruction": "pick up the red cube"
  }'
```

#### **Scenario B: You're using SSH tunnel**

If you set up SSH tunnel:

```bash
# 1. In one terminal, keep SSH tunnel open:
ssh -L 8000:localhost:8000 -L 3000:localhost:3000 your-username@fau-computer

# 2. In another terminal, test locally:
curl http://localhost:8000/health

# 3. Open browser:
# http://localhost:3000  (Grafana)
# http://localhost:8000/docs  (API docs)
```

#### **Scenario C: FAU computer has public IP**

If FAU computer has public IP (rare):

```bash
# Check firewall allows port 8000
# Then test directly
curl http://public-ip:8000/health
```

---

## 📊 Complete Workflow Diagram

```
┌─────────────────────────────────────────────────────────┐
│  YOUR MAC (at home)                                     │
│  ┌────────────────────────────────────┐                │
│  │ 1. Connect to FAU VPN              │                │
│  │    (if required)                   │                │
│  └────────────┬───────────────────────┘                │
│               │                                          │
│  ┌────────────▼───────────────────────┐                │
│  │ 2. SSH to FAU computer             │                │
│  │    ssh user@fau-computer           │                │
│  └────────────┬───────────────────────┘                │
└───────────────┼──────────────────────────────────────────┘
                │
                │ SSH/VPN connection
                │
┌───────────────▼──────────────────────────────────────────┐
│  FAU COMPUTER (on FAU wifi)                              │
│  ┌────────────────────────────────────┐                 │
│  │ 3. Clone or copy VLAAPI code       │                 │
│  │    git clone ... or rsync          │                 │
│  └────────────┬───────────────────────┘                 │
│               │                                           │
│  ┌────────────▼───────────────────────┐                 │
│  │ 4. Run deployment script           │                 │
│  │    ./scripts/remote_gpu_deploy.sh  │                 │
│  └────────────┬───────────────────────┘                 │
│               │                                           │
│  ┌────────────▼───────────────────────┐                 │
│  │ 5. API running on port 8000        │                 │
│  │    with Titan X GPUs               │                 │
│  └────────────┬───────────────────────┘                 │
└───────────────┼──────────────────────────────────────────┘
                │
                │ HTTP requests via VPN
                │
┌───────────────▼──────────────────────────────────────────┐
│  YOUR MAC (at home)                                      │
│  ┌────────────────────────────────────┐                 │
│  │ 6. Test API from home              │                 │
│  │    curl http://fau-ip:8000/...     │                 │
│  └────────────────────────────────────┘                 │
└──────────────────────────────────────────────────────────┘
```

---

## 🔧 Practical Step-by-Step Commands

### **Complete Example (Using VPN method):**

```bash
# ============================================
# ON YOUR MAC AT HOME
# ============================================

# Step 1: Connect to FAU VPN
# (Open FAU VPN client and connect)

# Step 2: Find FAU computer's IP
# You need to know this - ask FAU IT or check your notes

# Step 3: Copy project to FAU computer
rsync -avz --progress \
  --exclude 'node_modules' \
  --exclude 'venv' \
  /Users/aniksahai/Desktop/VLAAPI/ \
  your-username@fau-computer-ip:~/VLAAPI/

# Step 4: SSH to FAU computer
ssh your-username@fau-computer-ip

# ============================================
# NOW YOU'RE ON THE FAU COMPUTER
# ============================================

# Step 5: Navigate to project
cd ~/VLAAPI

# Step 6: Run deployment
chmod +x scripts/remote_gpu_deploy.sh
./scripts/remote_gpu_deploy.sh

# Wait 10-15 minutes...
# At the end, you'll see an API key. SAVE IT!

# Step 7: Get FAU computer's IP
hostname -I
# Example output: 10.192.45.123

# Step 8: Exit SSH
exit

# ============================================
# BACK ON YOUR MAC AT HOME
# ============================================

# Step 9: Test the API (still connected to FAU VPN)
export FAU_IP="10.192.45.123"  # Use the IP from Step 7
export API_KEY="vla_remote_abc123..."  # Use the key from Step 6

# Test health
curl http://$FAU_IP:8000/health

# Test inference
curl -X POST http://$FAU_IP:8000/v1/inference \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openvla-7b",
    "image": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    "instruction": "pick up the red cube"
  }' | jq

# Step 10: View dashboards in browser
# http://10.192.45.123:3000  (Grafana - login: admin/admin123)
# http://10.192.45.123:8000/docs  (API documentation)
```

---

## 🔑 Getting FAU Computer Information

### **Before You Start, You Need:**

1. **Username** on FAU computer
   - Your FAU student/faculty username

2. **Password** for FAU computer
   - Your FAU password or SSH key

3. **FAU computer's IP address**
   - Internal IP (if on VPN): `10.x.x.x`
   - Public IP (rare): `134.68.x.x`
   
   **How to get it:**
   ```bash
   # If you can physically access the FAU computer:
   hostname -I
   
   # Or remotely (if you already have access):
   ssh user@fau-computer
   hostname -I
   ```

4. **FAU VPN access** (if required)
   - Contact FAU IT: it@fau.edu
   - Usually they provide Cisco AnyConnect

---

## 🌐 Network Scenarios

### **Scenario 1: You Have VPN Access ✅ (Best Option)**

```bash
# 1. Connect to FAU VPN from home
# 2. Access FAU computer's internal IP
# 3. Full access to all services

# From your Mac:
ssh your-username@10.x.x.x  # Internal IP
curl http://10.x.x.x:8000/health
```

**Advantages:**
- ✅ Full access to FAU network
- ✅ Can access all ports
- ✅ Most secure

### **Scenario 2: SSH Tunnel (If you have SSH access)**

```bash
# Create tunnel for multiple ports
ssh -L 8000:localhost:8000 \
    -L 3000:localhost:3000 \
    -L 9090:localhost:9090 \
    your-username@fau-computer

# Then access via localhost on your Mac:
curl http://localhost:8000/health
# Open browser: http://localhost:3000
```

**Advantages:**
- ✅ Works if you have SSH access
- ✅ Encrypts all traffic
- ⚠️ Must keep terminal open

### **Scenario 3: FAU Computer Has Public IP (Rare)**

```bash
# If FAU gave you a public IP, direct access:
curl http://134.68.x.x:8000/health
```

**Considerations:**
- ⚠️ Check with FAU IT if allowed
- ⚠️ Firewall rules must allow ports
- ⚠️ Less secure (add authentication)

---

## 📝 Quick Setup Script

Save this as `setup_remote_fau.sh`:

```bash
#!/bin/bash
# Setup script for FAU computer access

echo "🎓 FAU Computer Setup"
echo ""

# Get information
read -p "Your FAU username: " FAU_USER
read -p "FAU computer IP address: " FAU_IP

echo ""
echo "Step 1: Copying project to FAU computer..."
rsync -avz --progress \
  --exclude 'node_modules' \
  --exclude 'venv' \
  --exclude '.git' \
  /Users/aniksahai/Desktop/VLAAPI/ \
  ${FAU_USER}@${FAU_IP}:~/VLAAPI/

echo ""
echo "Step 2: Deploying on FAU computer..."
ssh ${FAU_USER}@${FAU_IP} << 'ENDSSH'
cd ~/VLAAPI
chmod +x scripts/remote_gpu_deploy.sh
./scripts/remote_gpu_deploy.sh
ENDSSH

echo ""
echo "✅ Setup complete!"
echo ""
echo "To test from your Mac:"
echo "  export FAU_IP='${FAU_IP}'"
echo "  curl http://\$FAU_IP:8000/health"
```

Run it:
```bash
chmod +x setup_remote_fau.sh
./setup_remote_fau.sh
```

---

## 🐛 Troubleshooting

### **Problem: Can't SSH to FAU computer**

```bash
# Try:
# 1. Check if you're on FAU VPN
# 2. Ping the computer
ping fau-computer-ip

# 3. Check SSH is running
# (need physical access or contact FAU IT)
```

**Solution:** Contact FAU IT for VPN access or SSH setup

### **Problem: Connection times out**

```bash
# Likely firewall blocking ports
# On FAU computer (if you have sudo):
sudo ufw allow 8000/tcp
sudo ufw allow 3000/tcp
```

**Solution:** Contact FAU IT to open required ports

### **Problem: Can't copy files (permission denied)**

```bash
# Check if you can write to home directory
ssh user@fau-computer
cd ~
touch test.txt  # Should work
rm test.txt
```

**Solution:** Make sure you're using correct username/password

### **Problem: Forgot to save API key**

```bash
# SSH to FAU computer
ssh user@fau-computer
cd ~/VLAAPI

# Retrieve API key from database
docker exec vlaapi-postgres-remote psql -U vlaapi -d vlaapi -c \
  "SELECT key_prefix FROM api_keys LIMIT 1;"
```

---

## ✅ Success Checklist

- [ ] Can SSH to FAU computer (directly or via VPN)
- [ ] Copied VLAAPI code to FAU computer
- [ ] Ran deployment script successfully
- [ ] Got API key and saved it
- [ ] Can access http://fau-ip:8000/health from Mac
- [ ] Can make inference requests
- [ ] Can view Grafana dashboard

**All ✅ → You're ready to test!** 🎉

---

## 📚 Quick Reference

### **Essential Commands**

```bash
# Copy code to FAU
rsync -avz /Users/aniksahai/Desktop/VLAAPI/ user@fau-ip:~/VLAAPI/

# SSH to FAU
ssh user@fau-ip

# Deploy on FAU
cd ~/VLAAPI && ./scripts/remote_gpu_deploy.sh

# Test from Mac (via VPN)
curl http://fau-ip:8000/health

# SSH tunnel (if no VPN)
ssh -L 8000:localhost:8000 user@fau-ip
```

### **Ports You Need Access To**

| Port | Service | Required? |
|------|---------|-----------|
| 22 | SSH | ✅ Yes |
| 8000 | API | ✅ Yes |
| 3000 | Grafana | Optional |
| 9090 | Prometheus | Optional |

---

## 🎯 Summary

**Your situation:**
- Mac at home ← Want to test from here
- FAU computer with GPUs ← Deploy API here

**Solution:**
1. **Connect:** Use FAU VPN or SSH tunnel
2. **Copy:** Use rsync or git clone
3. **Deploy:** Run `./scripts/remote_gpu_deploy.sh`
4. **Test:** Use curl or browser

**Most likely you need:** FAU VPN access from IT department

---

## 📞 FAU IT Contact

If you need help:
- **FAU IT Email:** it@fau.edu
- **FAU Help Desk:** (561) 297-3999
- **VPN Request:** Ask for "VPN access for remote research computing"

---

**Ready to start?** Follow the step-by-step commands above! 🚀

