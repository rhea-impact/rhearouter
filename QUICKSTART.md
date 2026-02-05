# RheaRouter Quick Start

Get RheaRouter running in **60 seconds** with this step-by-step guide.

---

## Prerequisites

Before starting, ensure you have:

- **Linux system** (tested on Ubuntu 22.04+)
- **Python 3.12+** installed
- **Ollama** installed and running
- **8GB+ VRAM** (for vision models)
- **25GB+ free disk space** (for models)

---

## 🚀 60-Second Setup

### Step 1: Verify Ollama

```bash
# Check if Ollama is running
systemctl status ollama

# If not running, start it
systemctl start ollama

# Verify it's working
ollama list
```

### Step 2: Clone & Install

```bash
# Navigate to the repository
cd /home/djshanklin/repos/rhearouter

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (takes ~30 seconds)
pip install -r requirements.txt
```

### Step 3: Start RheaRouter

```bash
# Start the server
uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# You should see:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# {"message": "Ollama connection established"}
```

### Step 4: Test It!

Open a new terminal and test:

```bash
# Health check
curl http://localhost:8000/health

# Chat completion
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Say hello!"}
    ]
  }'
```

**✅ Done!** RheaRouter is running.

---

## 📝 What Just Happened?

1. **Ollama Health Check** - Verified connection to local LLM server
2. **Model Loading** - RheaRouter can now access your Ollama models
3. **Middleware Stack** - Rate limiting and VRAM management active
4. **API Ready** - OpenAI-compatible endpoint listening on port 8000

---

## 🎯 Next Steps

### Test Different Models

```bash
# Use specific model
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-r1:8b",
    "messages": [{"role": "user", "content": "What is 2+2?"}]
  }'

# Auto-select model (omit "model" field)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### Test Vision Models

```bash
# Send image (base64 encoded)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "minicpm-v:8b",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "What do you see?"},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
      ]
    }]
  }'
```

### Check Available Models

```bash
# List all models (OpenAI-compatible format)
curl http://localhost:8000/v1/models
```

---

## ⚙️ Configuration (Optional)

Create `.env` file for custom configuration:

```bash
# Copy template
cp .env.example .env

# Edit settings
nano .env
```

**Common settings:**

```bash
# Change port
PORT=8080

# Adjust rate limits
GLOBAL_RATE_LIMIT=120      # 120 req/min
PER_CLIENT_RATE_LIMIT=40   # 40 req/min per IP

# VRAM management
VISION_SLOTS=1  # Max concurrent vision requests
TEXT_SLOTS=2    # Max concurrent text requests

# Logging
LOG_LEVEL=DEBUG  # More verbose logs
```

**Restart server after changes:**

```bash
# Press Ctrl+C to stop
# Then restart:
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

---

## 🔧 Troubleshooting

### "Ollama connection failed"

```bash
# Check if Ollama is running
systemctl status ollama

# Check if Ollama is accessible
curl http://localhost:11434/api/tags

# If not running, start it
systemctl start ollama
```

### "Model not found: ..."

```bash
# List installed models
ollama list

# Pull missing model
ollama pull llama3.1:8b
ollama pull minicpm-v:8b
```

### "Address already in use"

```bash
# Find what's using port 8000
lsof -i:8000

# Kill the process
kill -9 <PID>

# Or use a different port
uvicorn src.api.main:app --port 8001
```

### "Import error" or "Module not found"

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### "429 Too Many Requests"

You hit the rate limit! Wait a minute or adjust limits in `.env`:

```bash
GLOBAL_RATE_LIMIT=120      # Increase from 60
PER_CLIENT_RATE_LIMIT=40   # Increase from 20
```

---

## 📚 Learn More

- **[README.md](README.md)** - Full documentation
- **[API.md](API.md)** - Complete API reference
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design
- **[examples/](examples/)** - Usage examples

---

## 🎓 Advanced Usage

### Run with Auto-Reload (Development)

```bash
uvicorn src.api.main:app --reload
```

Changes to code will automatically restart the server.

### Run in Background

```bash
# Start in background
nohup uvicorn src.api.main:app > rhearouter.log 2>&1 &

# Check logs
tail -f rhearouter.log

# Stop server
pkill -f "uvicorn.*rhearouter"
```

### Run with Systemd (Production)

See `/logs/2026-02-04-session/implementation-plan.md` for systemd service configuration.

---

## ✅ Verification Checklist

Before considering setup complete, verify:

- [ ] Health endpoint returns `{"status": "healthy"}`
- [ ] Models endpoint returns list of models
- [ ] Chat completion returns a response
- [ ] Server logs show "Ollama connection established"
- [ ] No errors in terminal output
- [ ] Rate limiting works (try 10+ rapid requests)
- [ ] Request ID appears in response headers

---

## 🆘 Still Having Issues?

1. Check server logs for errors
2. Verify Python version: `python3 --version` (need 3.12+)
3. Verify Ollama: `ollama list`
4. Check disk space: `df -h`
5. Review logs at `/logs/2026-02-04-session/`

---

**Questions?** See [API.md](API.md) for endpoint details or [ARCHITECTURE.md](ARCHITECTURE.md) for how the system works.

**Ready to build!** 🚀
