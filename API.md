# RheaRouter API Reference

Complete API documentation for RheaRouter's OpenAI-compatible inference server.

---

## Base URL

```
http://localhost:8000
```

---

## Authentication

Currently using API key authentication (configurable via environment).

```bash
# Include API key in Authorization header
curl -H "Authorization: Bearer your-api-key-here" \
  http://localhost:8000/v1/chat/completions
```

**Note:** Authentication can be disabled for local development by setting `FEATURE_AUTH=false` in `.env`.

---

## Rate Limiting

RheaRouter implements two-tier token bucket rate limiting:

- **Global limit:** 60 requests/minute across all clients
- **Per-client limit:** 20 requests/minute per IP address
- **Burst capacity:** 10 tokens (global), 5 tokens (per-client)

### Rate Limit Headers

All responses include rate limit information:

```
X-RateLimit-Limit: 20
X-RateLimit-Remaining: 15
X-RateLimit-Reset: 1234567890
```

### Rate Limit Exceeded

When rate limit is exceeded, the server returns HTTP 429:

```json
{
  "error": {
    "message": "Rate limit exceeded. Try again in 30 seconds.",
    "type": "rate_limit_error",
    "code": "rate_limit_exceeded",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Headers:**
- `Retry-After: 30` - Seconds until next request allowed

---

## Endpoints

### 1. Health Check

Check server health and Ollama connectivity.

**Endpoint:** `GET /health`

**Request:**
```bash
curl http://localhost:8000/health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "ollama": "connected",
  "timestamp": "2026-02-04T20:15:23.456Z"
}
```

**Response (503 Service Unavailable):**
```json
{
  "status": "unhealthy",
  "ollama": "disconnected",
  "error": "Ollama connection failed"
}
```

---

### 2. List Models

Get all available models from Ollama.

**Endpoint:** `GET /v1/models`

**Request:**
```bash
curl http://localhost:8000/v1/models
```

**Response (200 OK):**
```json
{
  "object": "list",
  "data": [
    {
      "id": "llama3.1:8b",
      "object": "model",
      "created": 1234567890,
      "owned_by": "ollama"
    },
    {
      "id": "minicpm-v:8b",
      "object": "model",
      "created": 1234567890,
      "owned_by": "ollama"
    }
  ]
}
```

**Notes:**
- OpenAI-compatible format
- Models must be pulled via Ollama first: `ollama pull llama3.1:8b`

---

### 3. Chat Completions

**Endpoint:** `POST /v1/chat/completions`

OpenAI-compatible chat completions with automatic model selection.

#### Request Format

```json
{
  "model": "llama3.1:8b",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "What is 2+2?"
    }
  ],
  "temperature": 0.7,
  "max_tokens": 2048,
  "top_p": 1.0,
  "stop": null
}
```

#### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `model` | string | No | Auto-selected | Model to use. Omit for auto-selection. |
| `messages` | array | Yes | - | Array of message objects |
| `temperature` | float | No | 0.7 | Sampling temperature (0.0-2.0) |
| `max_tokens` | integer | No | 2048 | Max tokens to generate (1-32000) |
| `top_p` | float | No | 1.0 | Nucleus sampling parameter |
| `stop` | array | No | null | Stop sequences |

#### Message Object

**Text message:**
```json
{
  "role": "user",
  "content": "Hello!"
}
```

**Multimodal message (vision models):**
```json
{
  "role": "user",
  "content": [
    {
      "type": "text",
      "text": "What do you see in this image?"
    },
    {
      "type": "image_url",
      "image_url": {
        "url": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
      }
    }
  ]
}
```

**Roles:**
- `system` - System instructions (optional)
- `user` - User message
- `assistant` - Assistant response (for multi-turn)

---

#### Response Format

```json
{
  "id": "chatcmpl-550e8400-e29b-41d4-a716-446655440000",
  "object": "chat.completion",
  "created": 1738699523,
  "model": "llama3.1:8b",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "2 + 2 = 4",
        "name": null
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 23,
    "completion_tokens": 8,
    "total_tokens": 31
  }
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique request ID (UUID4) |
| `object` | string | Always "chat.completion" |
| `created` | integer | Unix timestamp |
| `model` | string | Model used for generation |
| `choices` | array | Array of completion choices |
| `usage` | object | Token usage statistics |

**Choice object:**
- `index` - Choice index (always 0)
- `message` - Generated message
- `finish_reason` - Why generation stopped ("stop", "length")

**Usage object:**
- `prompt_tokens` - Tokens in prompt (estimated)
- `completion_tokens` - Tokens in completion (estimated)
- `total_tokens` - Sum of prompt + completion

---

#### Auto Model Selection

If `model` is omitted, RheaRouter selects automatically:

**Vision requests** (messages contain images):
- Selected: `minicpm-v:8b` (configured as `DEFAULT_VISION_MODEL`)

**Text requests** (no images):
- Selected: `llama3.1:8b` (configured as `DEFAULT_TEXT_MODEL`)

**Example:**
```bash
# Auto-selects text model
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

---

#### Examples

**1. Simple Text Completion**

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1:8b",
    "messages": [
      {"role": "user", "content": "What is the capital of France?"}
    ],
    "temperature": 0.7,
    "max_tokens": 100
  }'
```

**Response:**
```json
{
  "id": "chatcmpl-12345",
  "object": "chat.completion",
  "created": 1738699523,
  "model": "llama3.1:8b",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "The capital of France is Paris."
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 8,
    "total_tokens": 18
  }
}
```

---

**2. Multi-Turn Conversation**

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1:8b",
    "messages": [
      {"role": "user", "content": "My name is Alice"},
      {"role": "assistant", "content": "Hello Alice! Nice to meet you."},
      {"role": "user", "content": "What is my name?"}
    ]
  }'
```

**Response:**
```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "Your name is Alice."
    }
  }]
}
```

---

**3. Vision Request (Image Analysis)**

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "minicpm-v:8b",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "What do you see in this image?"},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,/9j/4AAQ..."}}
      ]
    }]
  }'
```

**Image Format:**
- Data URL: `data:image/jpeg;base64,<base64-encoded-image>`
- Supported formats: JPEG, PNG, WebP, GIF
- Max size: 10MB per image

---

**4. Temperature Control**

```bash
# Creative (high temperature)
curl -X POST http://localhost:8000/v1/chat/completions \
  -d '{
    "messages": [{"role": "user", "content": "Write a poem"}],
    "temperature": 1.5
  }'

# Deterministic (low temperature)
curl -X POST http://localhost:8000/v1/chat/completions \
  -d '{
    "messages": [{"role": "user", "content": "What is 2+2?"}],
    "temperature": 0.1
  }'
```

---

**5. Token Limit**

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -d '{
    "messages": [{"role": "user", "content": "Explain quantum physics"}],
    "max_tokens": 50
  }'
```

**Notes:**
- Generation stops when `max_tokens` is reached
- `finish_reason` will be `"length"` instead of `"stop"`

---

## Error Responses

All errors follow OpenAI's error format and include the request ID for debugging.

### Error Format

```json
{
  "error": {
    "message": "Human-readable error message",
    "type": "error_type",
    "code": "error_code",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

---

### HTTP Status Codes

| Code | Type | Description |
|------|------|-------------|
| 200 | Success | Request completed successfully |
| 400 | Bad Request | Invalid request format |
| 404 | Not Found | Model not found |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server error |
| 503 | Service Unavailable | Ollama unavailable or model loading |
| 504 | Gateway Timeout | Request timed out |

---

### Error Examples

**1. Model Not Found (404)**

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -d '{"model": "nonexistent:model", "messages": [...]}'
```

**Response:**
```json
{
  "error": {
    "message": "Model not found: nonexistent:model",
    "type": "invalid_request_error",
    "code": "model_not_found",
    "request_id": "12345"
  }
}
```

---

**2. Validation Error (422)**

```bash
# Missing required field
curl -X POST http://localhost:8000/v1/chat/completions \
  -d '{"model": "llama3.1:8b"}'
```

**Response:**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "messages"],
      "msg": "Field required",
      "input": {"model": "llama3.1:8b"}
    }
  ]
}
```

---

**3. Rate Limit Exceeded (429)**

```bash
# After 20 requests in 1 minute from same IP
curl -X POST http://localhost:8000/v1/chat/completions \
  -d '{"messages": [...]}'
```

**Response:**
```json
{
  "error": {
    "message": "Rate limit exceeded. Try again in 30 seconds.",
    "type": "rate_limit_error",
    "code": "rate_limit_exceeded",
    "request_id": "12345"
  }
}
```

**Headers:**
- `Retry-After: 30`

---

**4. Service Unavailable (503)**

```bash
# Ollama is down or model failed to load
curl -X POST http://localhost:8000/v1/chat/completions \
  -d '{"messages": [...]}'
```

**Response:**
```json
{
  "error": {
    "message": "Ollama service unavailable",
    "type": "service_error",
    "code": "service_unavailable",
    "request_id": "12345"
  }
}
```

---

**5. Gateway Timeout (504)**

```bash
# Request took longer than configured timeout (300s default)
curl -X POST http://localhost:8000/v1/chat/completions \
  -d '{"messages": [...], "max_tokens": 50000}'
```

**Response:**
```json
{
  "error": {
    "message": "Request timed out",
    "type": "timeout_error",
    "code": "request_timeout",
    "request_id": "12345"
  }
}
```

---

## Request Headers

### Optional Headers

| Header | Description | Example |
|--------|-------------|---------|
| `Authorization` | API key authentication | `Bearer your-key` |
| `X-Forwarded-For` | Client IP (for rate limiting) | `192.168.1.100` |
| `Content-Type` | Must be `application/json` | `application/json` |

---

## Response Headers

All responses include:

| Header | Description | Example |
|--------|-------------|---------|
| `X-Request-ID` | Unique request identifier (UUID4) | `550e8400-e29b-41d4-a716-446655440000` |
| `Content-Type` | Response format | `application/json` |
| `X-RateLimit-Limit` | Max requests per minute | `20` |
| `X-RateLimit-Remaining` | Remaining requests | `15` |
| `X-RateLimit-Reset` | Reset timestamp (Unix) | `1738699523` |

**On rate limit exceeded:**
- `Retry-After` - Seconds until next request allowed

---

## VRAM Flow Valve

RheaRouter implements intelligent request queueing to prevent VRAM exhaustion:

**Concurrency limits:**
- **Vision models:** 1 concurrent request
- **Text models:** 2 concurrent requests

**Behavior:**
- Requests queue if slots are full
- FIFO processing order
- No timeout (requests wait indefinitely)

**Vision model detection:**
Model name contains any of: `vl`, `llava`, `minicpm-v`, `vision`

**Example:**
```bash
# If 1 vision request is processing, next vision request waits
# Text requests can proceed (separate slot pool)
```

---

## Configuration

Configure via environment variables:

```bash
# Rate Limiting
GLOBAL_RATE_LIMIT=60        # req/min (all clients)
PER_CLIENT_RATE_LIMIT=20    # req/min per IP
RATE_LIMIT_BURST=10         # burst capacity

# VRAM Flow Valve
VISION_SLOTS=1              # concurrent vision requests
TEXT_SLOTS=2                # concurrent text requests

# Ollama Backend
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TIMEOUT=300          # seconds

# Model Defaults
DEFAULT_TEXT_MODEL=llama3.1:8b
DEFAULT_VISION_MODEL=minicpm-v:8b
REASONING_MODEL=deepseek-r1:8b

# Logging
LOG_LEVEL=INFO
DEBUG=false
```

See [QUICKSTART.md](QUICKSTART.md) for complete configuration guide.

---

## OpenAI Compatibility

RheaRouter is compatible with OpenAI's Python SDK and most OpenAI clients.

### Python SDK Example

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="your-key"  # or "not-needed" if auth disabled
)

response = client.chat.completions.create(
    model="llama3.1:8b",
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)

print(response.choices[0].message.content)
```

### What's Supported

✅ Chat completions (`/v1/chat/completions`)
✅ Model listing (`/v1/models`)
✅ Multimodal content (images)
✅ Temperature, max_tokens, top_p, stop
✅ Message history (multi-turn)
✅ Token usage tracking

### What's Not Supported (Yet)

❌ Streaming responses (`"stream": true`)
❌ Function calling / tools
❌ Embeddings endpoint
❌ Audio/TTS endpoints
❌ Fine-tuning

**Roadmap:** Streaming support planned for Phase 3 (Week 4-5).

---

## Performance

**Observed latency** (Lenovo ThinkPad P16, RTX A2000 8GB):

| Request Type | Latency | VRAM |
|--------------|---------|------|
| Text completion | 1-3s | 4.5GB |
| Vision analysis | 3-5s | 5.5GB |
| Multi-turn (3 messages) | 2-4s | 4.5GB |

**Throughput:**
- **Sequential:** 100-200 text req/hour, 10-20 vision req/hour
- **Concurrent:** 2 text requests in parallel, 1 vision request

**Token estimation accuracy:** ±20% (uses 4 chars/token heuristic)

---

## Debugging

### Request ID Tracking

Every request gets a unique ID (UUID4):

```bash
curl -v http://localhost:8000/v1/chat/completions \
  -d '{"messages": [...]}'

# Response headers:
< X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

Use request ID to:
- Track requests in logs
- Debug errors
- Report issues

### Logs

View structured JSON logs:

```bash
# If running with systemd
sudo journalctl -u rhearouter -f

# If running manually
tail -f rhearouter.log
```

**Log format:**
```json
{
  "timestamp": "2026-02-04T20:15:23.456Z",
  "level": "INFO",
  "message": "Chat completion",
  "request_id": "550e8400-...",
  "model": "llama3.1:8b",
  "duration_ms": 2341
}
```

---

## API Changelog

### v0.1.0 (Current - Feb 2026)

**Added:**
- `POST /v1/chat/completions` - OpenAI-compatible chat endpoint
- `GET /v1/models` - List available models
- `GET /health` - Health check
- Auto model selection (vision vs text)
- Rate limiting (60/min global, 20/min per-client)
- VRAM flow valve (1 vision, 2 text slots)
- Request ID tracking
- Multimodal image support
- Token usage estimation

**Coming in Phase 2 (Week 3):**
- Intelligent model routing
- Request/response persistence (SQLite)
- Analytics queries

**Coming in Phase 3 (Week 4-5):**
- Streaming responses (`"stream": true`)
- Mixture-of-Agents support
- Speculative decoding

---

## Questions?

- **Setup issues:** See [QUICKSTART.md](QUICKSTART.md)
- **System design:** See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Examples:** See [examples/](examples/) directory
- **General info:** See [README.md](README.md)

---

**Happy inferencing!** 🚀
