# RheaRouter Examples

Practical examples for using RheaRouter's API.

---

## Files in This Directory

1. **`curl-examples.sh`** - Complete curl examples for all endpoints
2. **`python-client.py`** - Python client using OpenAI SDK
3. **`vision-example.sh`** - Multimodal (image + text) request
4. **`stress-test.sh`** - Load testing script

---

## Quick Start

### 1. Basic Text Completion

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What is 2+2?"}
    ]
  }'
```

### 2. Specific Model

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-r1:8b",
    "messages": [
      {"role": "user", "content": "Solve: If x^2 = 16, what is x?"}
    ]
  }'
```

### 3. Multi-Turn Conversation

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "My name is Alice"},
      {"role": "assistant", "content": "Hello Alice! Nice to meet you."},
      {"role": "user", "content": "What is my name?"}
    ]
  }'
```

### 4. Python Client

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed"
)

response = client.chat.completions.create(
    model="llama3.1:8b",
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)

print(response.choices[0].message.content)
```

---

## Prerequisites

**Before running examples:**

1. RheaRouter is running:
   ```bash
   uvicorn src.api.main:app --host 0.0.0.0 --port 8000
   ```

2. Ollama is running:
   ```bash
   systemctl status ollama
   ```

3. Models are pulled:
   ```bash
   ollama list
   ```

---

## Running Examples

### Run All curl Examples

```bash
cd examples
bash curl-examples.sh
```

### Run Python Client

```bash
cd examples
python3 python-client.py
```

### Run Vision Example

```bash
cd examples
bash vision-example.sh /path/to/image.jpg
```

### Run Stress Test

```bash
cd examples
bash stress-test.sh 100  # 100 requests
```

---

## Environment Variables

Some examples use environment variables for configuration:

```bash
# API endpoint
export RHEA_URL="http://localhost:8000"

# API key (if auth enabled)
export RHEA_API_KEY="your-key-here"

# Default model
export RHEA_MODEL="llama3.1:8b"
```

---

## Expected Output

**Successful response:**
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
        "content": "2 + 2 equals 4."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 8,
    "total_tokens": 18
  }
}
```

**Error response (rate limited):**
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

---

## Tips

1. **Pretty-print JSON:**
   ```bash
   curl ... | jq '.'
   ```

2. **Save response:**
   ```bash
   curl ... > response.json
   ```

3. **Extract just the message:**
   ```bash
   curl ... | jq -r '.choices[0].message.content'
   ```

4. **Check rate limits:**
   ```bash
   curl -I ... | grep X-RateLimit
   ```

5. **Follow request ID:**
   ```bash
   REQUEST_ID=$(curl ... | jq -r '.id')
   # Search logs for $REQUEST_ID
   ```

---

## Troubleshooting

**"Connection refused"**
- Check RheaRouter is running: `curl http://localhost:8000/health`
- Check port: `lsof -i:8000`

**"Model not found"**
- List models: `curl http://localhost:8000/v1/models`
- Pull model: `ollama pull llama3.1:8b`

**"Rate limit exceeded"**
- Wait the `Retry-After` seconds
- Or restart RheaRouter (resets in-memory limits)

**"Timeout"**
- Increase `OLLAMA_TIMEOUT` in config
- Or reduce `max_tokens` in request

---

## More Examples

See full documentation:
- **API Reference:** [../API.md](../API.md)
- **Quick Start:** [../QUICKSTART.md](../QUICKSTART.md)
- **Architecture:** [../ARCHITECTURE.md](../ARCHITECTURE.md)
