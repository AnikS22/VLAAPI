# 🚀 START HERE - VLA Inference API

**New to APIs?** This guide will get you from zero to running in 10 minutes.

---

## 📚 What is this project?

This is an **API for robot control using AI**. 

You send:
- 📸 An image (what the robot sees)
- 💬 An instruction (what you want it to do)

You get back:
- 🤖 A robot action (7 numbers telling the robot how to move)

**Example:**
```
YOU SEND:  Image of a table with a red cube + "pick up the red cube"
YOU GET:   [0.15, -0.08, 0.22, 0.01, 0.05, -0.03, 1.0]
           ↓
           Robot moves to position (0.15, -0.08, 0.22) and closes gripper (1.0)
```

---

## ⚡ The Fastest Way to Get Started

### Option 1: Automated Setup (Easiest)

```bash
# 1. Run the setup script
./scripts/quick_setup.sh

# 2. Start the API
source venv/bin/activate
python -m uvicorn src.api.main:app --port 8000

# 3. Test it (in another terminal)
source venv/bin/activate
python examples/simple_api_test.py
```

### Option 2: Manual Setup (If script doesn't work)

```bash
# 1. Install Python packages
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Start database
docker-compose up -d postgres redis

# 3. Set up config
cp .env.example .env
# Edit .env and set USE_MOCK_MODELS=true

# 4. Start API
python -m uvicorn src.api.main:app --port 8000

# 5. Test (in another terminal)
curl http://localhost:8000/health
```

---

## 📖 Where to Learn More

### If you're new to programming:
→ **Start here:** `docs/BEGINNERS_API_GUIDE.md`
   - Explains APIs from scratch
   - Step-by-step setup
   - Simple examples

### If you know Python:
→ **Quick start:** `GETTING-STARTED.md`
   - Fast setup instructions
   - Code examples
   - Production deployment

### If you want complete details:
→ **Full system:** `docs/COMPLETE_SYSTEM_REPORT.md`
   - 1,688 lines of documentation
   - Every feature explained
   - Architecture diagrams

---

## 🎯 Quick Test

Once your API is running, try this:

```bash
# Test 1: Is it alive?
curl http://localhost:8000/health

# Test 2: Can I see the docs?
# Open in browser: http://localhost:8000/docs

# Test 3: Can I make a request?
python examples/simple_api_test.py
```

---

## 🤔 Common Questions

**Q: Do I need a GPU?**
A: No! Set `USE_MOCK_MODELS=true` to test without GPU.

**Q: Do I need a real robot?**
A: No! The API just returns actions. You can test without hardware.

**Q: What's an API key?**
A: Like a password for the API. Run `scripts/setup_database.py` to get one.

**Q: Why PostgreSQL and Redis?**
A: PostgreSQL stores data, Redis caches it. Both run in Docker.

**Q: Can I use this for research?**
A: Yes! Add your safety models in `src/services/custom_alignment.py`

---

## 🆘 Having Problems?

### Can't connect to API
```bash
# Make sure it's running
ps aux | grep uvicorn

# Check the port
netstat -an | grep 8000
```

### Database errors
```bash
# Check Docker containers
docker-compose ps

# Restart them
docker-compose down
docker-compose up -d postgres redis
```

### Python errors
```bash
# Make sure you're in virtual environment
which python
# Should show: /path/to/VLAAPI/venv/bin/python

# Reinstall packages
pip install -r requirements.txt
```

---

## 🎓 Learning Path

1. **Week 1: Get it running**
   - Follow this guide
   - Run simple_api_test.py
   - Read BEGINNERS_API_GUIDE.md

2. **Week 2: Understand how it works**
   - Read the code in src/api/
   - Try modifying examples/
   - Explore the interactive docs

3. **Week 3: Build something**
   - Add your robot config
   - Integrate with real hardware
   - Add custom safety checks

4. **Week 4: Deploy to production**
   - Set up real models (GPU)
   - Configure monitoring
   - Scale with Docker

---

## 📁 Important Files

```
VLAAPI/
├── START_HERE.md                    ← You are here
├── docs/BEGINNERS_API_GUIDE.md      ← Detailed tutorial
├── GETTING-STARTED.md               ← Quick setup
├── scripts/quick_setup.sh           ← Automated setup
├── examples/simple_api_test.py      ← Easy test script
│
├── src/api/main.py                  ← Main API code
├── src/api/routers/inference.py     ← Inference endpoint
├── src/services/vla_inference.py    ← AI model code
├── src/services/safety_monitor.py   ← Safety checks
│
├── .env                             ← Configuration
├── docker-compose.yml               ← Database setup
└── requirements.txt                 ← Python packages
```

---

## 🚦 Status Check

Before you start, make sure you have:

- [ ] Python 3.10+ installed
- [ ] Docker installed (for database)
- [ ] At least 4GB free RAM
- [ ] 2GB free disk space

Optional (for production):
- [ ] NVIDIA GPU with CUDA 12.1+
- [ ] 16GB+ RAM
- [ ] 50GB+ disk space (for AI models)

---

## 💡 The 3 Main Components

```
┌─────────────────────────────────────────────────┐
│  1. API SERVER (FastAPI + Python)               │
│     Receives requests, returns actions           │
│     Location: src/api/                           │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│  2. AI MODEL (OpenVLA / Mock)                   │
│     Processes image + text → robot action       │
│     Location: src/services/vla_inference.py     │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│  3. DATABASE (PostgreSQL + Redis)               │
│     Stores logs, metrics, API keys              │
│     Location: Docker containers                 │
└─────────────────────────────────────────────────┘
```

---

## 🎉 You're Ready!

**Next step:** Run the setup script!

```bash
./scripts/quick_setup.sh
```

Then read: `docs/BEGINNERS_API_GUIDE.md` for detailed examples.

**Questions?** Check the documentation in `docs/` folder.

**Good luck!** 🤖🚀

