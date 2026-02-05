---
name: rhearouter
description: Working with RheaRouter - local inference server with OpenAI-compatible API
triggers:
  - rhearouter
  - inference server
  - start server
  - test api
  - add model
  - ollama
  - rate limiting
  - vram
---

# RheaRouter - Local Inference Server

Production-grade self-hosted inference gateway with OpenAI-compatible API, intelligent model routing, and comprehensive observability.

## Quick Start

```bash
# Start the server
cd /home/djshanklin/repos/rhearouter
source venv/bin/activate
uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# Or with reload for development
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

## Testing the API

```bash
# Simple text request
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello!"}],
    "model": "llama3.1:8b"
  }'

# Vision request (image analysis)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "What is in this image?"},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
      ]
    }],
    "model": "minicpm-v:8b"
  }'

# Health check
curl http://localhost:8000/health

# List available models
curl http://localhost:8000/v1/models
```

## Project Structure

```
rhearouter/
├── src/
│   ├── api/
│   │   ├── main.py              # FastAPI app, middleware stack
│   │   └── routes/
│   │       ├── chat.py          # Chat completions endpoint
│   │       └── analytics.py     # Analytics and usage tracking
│   ├── backend/
│   │   ├── models.py            # Pydantic models (OpenAI/Ollama)
│   │   ├── message_utils.py     # Message format conversion
│   │   └── ollama_adapter.py    # HTTP client with retry logic
│   ├── core/
│   │   ├── config.py            # Configuration management
│   │   ├── router.py            # Intelligent model routing
│   │   └── persistence.py       # SQLite database for analytics
│   ├── middleware/
│   │   ├── request_id.py        # UUID generation
│   │   ├── rate_limiter.py      # Token bucket rate limiting
│   │   ├── vram_flow_valve.py   # VRAM-aware request queueing
│   │   └── error_handler.py     # Global error handling
│   ├── observability/
│   │   └── logging.py           # Structured JSON logging
│   └── tests/                   # Test suite (87 tests passing)
├── benchmark/                   # Vision model benchmarks (legacy)
├── examples/                    # Usage examples and scripts
├── logs/                        # Development session logs
└── docs/                        # Additional documentation
```

## Running Tests

```bash
# All tests
pytest src/tests/ -v

# Specific test suites
pytest src/tests/api/ -v           # API integration tests
pytest src/tests/middleware/ -v    # Middleware tests
pytest src/tests/backend/ -v       # Backend tests
pytest src/tests/core/ -v          # Core logic tests

# Current status: 87/87 passing ✅
```

## Adding New Models

```bash
# Pull a new model from Ollama
ollama pull modelname:tag

# Models are automatically discovered via /v1/models endpoint
# Update config.py DEFAULT_TEXT_MODEL or DEFAULT_VISION_MODEL if needed
```

## Configuration

Edit `.env` file or set environment variables:

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

# VRAM Management
VISION_SLOTS=1  # concurrent vision model requests
TEXT_SLOTS=2    # concurrent text model requests

# Model Defaults
DEFAULT_TEXT_MODEL=llama3.1:8b
DEFAULT_VISION_MODEL=minicpm-v:8b
REASONING_MODEL=deepseek-r1:8b
```

## Development Workflow

1. **Make changes** to code
2. **Write tests** for new features
3. **Run tests** to verify: `pytest src/tests/ -v`
4. **Test manually** with curl or examples
5. **Check logs** in `logs/` directory
6. **Commit** when all tests pass

## Common Tasks

### Adding a New Endpoint

1. Create route in `src/api/routes/`
2. Register in `src/api/main.py`
3. Add tests in `src/tests/api/`
4. Update API.md documentation

### Adding Middleware

1. Create middleware in `src/middleware/`
2. Register in `src/api/main.py` (order matters!)
3. Add tests in `src/tests/middleware/`
4. Update ARCHITECTURE.md

### Debugging Issues

```bash
# Check server logs
tail -f logs/*.log

# Check Ollama is running
curl http://localhost:11434/api/tags

# Verify models are loaded
ollama list

# Test Ollama directly
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.1:8b",
  "prompt": "Hello"
}'
```

## Key Implementation Details

### Middleware Stack Order (outermost to innermost)
1. **VRAM Flow Valve** - Queue requests based on available slots
2. **Rate Limiter** - Token bucket algorithm
3. **Request ID** - UUID generation
4. **Error Handler** - Catch all exceptions

### Model Selection Logic
- Auto-detects text vs vision based on message content
- Falls back to defaults if not specified
- Supports explicit model override via `model` parameter

### Retry Logic
- Exponential backoff: 1s, 2s, 4s
- Retries on connection errors and 5xx responses
- Max 3 attempts per request

## Documentation

- **[API.md](../../API.md)** - Complete API reference
- **[QUICKSTART.md](../../QUICKSTART.md)** - 60-second setup
- **[ARCHITECTURE.md](../../ARCHITECTURE.md)** - System design
- **[examples/](../../examples/)** - Usage patterns
- **[logs/2026-02-04-session/](../../logs/2026-02-04-session/)** - Implementation notes

## Troubleshooting

**Server won't start:**
- Check Ollama is running: `systemctl status ollama`
- Verify port 8000 is available: `lsof -i :8000`
- Check logs for errors

**Rate limited:**
- Increase limits in `.env`
- Check per-client limits (20/min default)

**VRAM errors:**
- Reduce concurrent slots in `.env`
- Monitor GPU usage: `nvidia-smi`

**Tests failing:**
- Ensure Ollama is running
- Check model availability: `ollama list`
- Review test output for specific failures
