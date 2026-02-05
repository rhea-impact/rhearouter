# RheaRouter

**Personal OpenRouter** - Production-grade self-hosted inference server with OpenAI-compatible API.

Transform your machine into a smart inference gateway with automatic model selection, rate limiting, VRAM management, and full observability.

[![Tests](https://img.shields.io/badge/tests-54%20passing-success)]() [![Python](https://img.shields.io/badge/python-3.12+-blue)]() [![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green)]()

---

## ✨ Features

### Production-Ready API
- **🔌 OpenAI-Compatible** - Drop-in replacement for `/v1/chat/completions`
- **🎯 Auto Model Selection** - Automatically chooses text vs vision models
- **🖼️ Multimodal Support** - Text + image inputs for vision models
- **📊 Token Estimation** - Usage tracking and reporting

### Smart Request Management
- **⚡ Rate Limiting** - Two-tier token bucket (60/min global, 20/min per-client)
- **🎮 VRAM Flow Valve** - Intelligent queueing (1 vision, 2 text concurrent slots)
- **🔄 Retry Logic** - Exponential backoff on transient failures
- **🆔 Request Tracking** - UUID for every request

### Production Quality
- **📝 Structured Logging** - JSON logs for monitoring and debugging
- **❌ Error Handling** - OpenAI-compatible error responses
- **🏥 Health Checks** - Liveness and readiness probes
- **✅ Tested** - 54 tests with 100% pass rate

---

## 🚀 Quick Start

**Get running in 60 seconds:**

```bash
# 1. Start Ollama (if not running)
systemctl start ollama

# 2. Install dependencies
cd /home/djshanklin/repos/rhearouter
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Start RheaRouter
uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# 4. Test it
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello!"}]}'
```

**See [QUICKSTART.md](QUICKSTART.md) for detailed setup.**

---

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get started in 60 seconds
- **[API.md](API.md)** - Complete API reference with examples
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design and data flow
- **[examples/](examples/)** - Example scripts and usage patterns

---

## 🏗️ Architecture

```
Request → VRAM Flow Valve → Rate Limiter → Request ID → Error Handler
              ↓                                                ↓
         Queue if busy                                   Catch all errors
              ↓                                                ↓
         Chat Endpoint ────────────────────────────────→ Response
              ↓
         Auto Model Selection
         (text vs vision)
              ↓
         Ollama Adapter
         (retry with backoff)
              ↓
         Local Models
```

**See [ARCHITECTURE.md](ARCHITECTURE.md) for details.**

---

## 🎯 API Endpoints

### Chat Completions

```bash
POST /v1/chat/completions
```

OpenAI-compatible chat endpoint with auto model selection:

```json
{
  "messages": [
    {"role": "user", "content": "What is 2+2?"}
  ],
  "temperature": 0.7,
  "max_tokens": 100
}
```

### Health & Discovery

- `GET /` - Service information
- `GET /health` - Health check
- `GET /v1/models` - List available models

**See [API.md](API.md) for complete reference.**

---

## 🤖 Installed Models

| Model | Size | Type | Use Case |
|-------|------|------|----------|
| `llama3.1:8b` | 4.9GB | Text | Fast general-purpose |
| `qwen2.5:7b` | 4.7GB | Text | High-quality generation |
| `deepseek-r1:8b` | 5.2GB | Text | Reasoning & logic |
| `minicpm-v:8b` | 5.5GB | Vision | OCR & image analysis |
| `llava:7b` | 4.7GB | Vision | Image understanding |

**Total:** 24.8GB

---

## ⚙️ Configuration

Configure via environment variables or `.env` file:

```bash
# Server
HOST=0.0.0.0
PORT=8000

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TIMEOUT=300

# Rate Limiting
GLOBAL_RATE_LIMIT=60       # requests per minute
PER_CLIENT_RATE_LIMIT=20   # requests per minute per IP
RATE_LIMIT_BURST=10        # burst allowance

# VRAM Management
VISION_SLOTS=1  # concurrent vision model requests
TEXT_SLOTS=2    # concurrent text model requests

# Model Defaults
DEFAULT_TEXT_MODEL=llama3.1:8b
DEFAULT_VISION_MODEL=minicpm-v:8b
REASONING_MODEL=deepseek-r1:8b

# Logging
LOG_LEVEL=INFO
DEBUG=false
```

---

## 📂 Project Structure

```
rhearouter/
├── src/
│   ├── api/
│   │   ├── main.py              # FastAPI app, middleware registration
│   │   └── routes/
│   │       └── chat.py          # Chat completions endpoint
│   ├── backend/
│   │   ├── models.py            # Pydantic models (OpenAI/Ollama)
│   │   ├── message_utils.py     # Message format conversion
│   │   └── ollama_adapter.py    # HTTP client with retry logic
│   ├── middleware/
│   │   ├── request_id.py        # UUID generation
│   │   ├── rate_limiter.py      # Token bucket rate limiting
│   │   ├── vram_flow_valve.py   # VRAM-aware request queueing
│   │   └── error_handler.py     # Global error handling
│   ├── core/
│   │   └── config.py            # Configuration management
│   ├── observability/
│   │   └── logging.py           # Structured JSON logging
│   └── tests/                   # 54 tests (100% passing)
│       ├── api/                 # Integration tests
│       ├── backend/             # Backend unit tests
│       └── middleware/          # Middleware tests
├── logs/                        # Development logs
├── examples/                    # Usage examples
├── docs/                        # Additional documentation
└── benchmark/                   # Vision model benchmarks (legacy)
```

---

## 🧪 Testing

```bash
# Run all tests
source venv/bin/activate
pytest src/tests/ -v

# Run specific test suite
pytest src/tests/api/ -v           # API integration tests
pytest src/tests/middleware/ -v    # Middleware tests
pytest src/tests/backend/ -v       # Backend tests

# Current status: 54/54 passing ✅
```

**Test Coverage:**
- API integration: 9 tests
- Middleware: 25 tests
- Backend: 20 tests

---

## 💻 Hardware Requirements

**Minimum:**
- CPU: 8+ cores
- RAM: 16GB
- VRAM: 8GB (for vision models)
- Storage: 30GB

**Recommended:**
- CPU: 16+ cores (for concurrent requests)
- RAM: 32GB (for multi-model scenarios)
- VRAM: 12GB+ (RTX 3060 or better)
- Storage: 50GB (room for more models)

**Tested On:**
- Lenovo ThinkPad P16 Gen 1
- Intel i9-12950HX (16 cores)
- 32GB RAM
- NVIDIA RTX A2000 (8GB VRAM)

---

## 📊 Performance

**Observed Latency** (on test hardware):
- Text completion: 1-3 seconds
- Vision completion: 3-5 seconds
- Multi-turn conversation: 2-4 seconds

**Throughput:**
- Sequential: 100-200 requests/hour (text), 10-20 requests/hour (vision)
- Concurrent: 2 text requests in parallel, 1 vision request

**Rate Limits:**
- Global: 60 requests/minute
- Per-client: 20 requests/minute
- Enforced via token bucket algorithm

---

## 🗺️ Roadmap

### ✅ Phase 1: Foundation (COMPLETE)
- [x] FastAPI application with OpenAI-compatible API
- [x] Rate limiting and VRAM flow control
- [x] Ollama backend integration with retry logic
- [x] Middleware stack (4 components)
- [x] Comprehensive test suite

### 🔄 Phase 2: Model Management (Week 3)
- [ ] Intelligent model routing with semantic analysis
- [ ] SQLite persistence for request/response logging
- [ ] Analytics queries and usage tracking
- [ ] Fallback strategies (primary → backup → 503)

### ⏳ Phase 3: Advanced Features (Week 4-5)
- [ ] Mixture-of-Agents (MoA) support
- [ ] Speculative decoding for speedup
- [ ] Ensemble OCR plugin (from benchmark work)
- [ ] Streaming responses (`"stream": true`)

### ⏳ Phase 4: Observability (Week 6)
- [ ] Prometheus metrics endpoint
- [ ] Grafana dashboards
- [ ] Performance monitoring
- [ ] Alerting rules

**See** `/logs/2026-02-04-session/implementation-plan.md` **for complete 6-week plan.**

---

## 🤝 Contributing

This is a personal project, but improvements are welcome!

1. Fork the repository
2. Create a feature branch
3. Write tests for new features
4. Ensure all tests pass (`pytest src/tests/`)
5. Submit a pull request

**Code Style:**
- Follow PEP 8
- Use type hints
- Add docstrings to all public functions
- Keep functions small and focused

---

## 📜 License

Private - Personal use

---

## 🙏 Acknowledgments

- **FastAPI** - Modern Python web framework
- **Ollama** - Local LLM runtime
- **Pydantic** - Data validation
- **Claude Code** - AI-assisted development

---

## 📞 Support

For issues or questions:
1. Check [API.md](API.md) for endpoint documentation
2. Check [ARCHITECTURE.md](ARCHITECTURE.md) for system design
3. Review logs at `/logs/2026-02-04-session/`
4. Run health check: `curl http://localhost:8000/health`

---

**Built with ❤️ using Claude Code - Your personal inference server is ready!**
