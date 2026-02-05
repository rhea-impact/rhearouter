# RheaRouter 2026: Personal Inference Server Implementation Plan

**Date:** February 4, 2026
**System:** Lenovo ThinkPad P16 Gen 1 (RTX A2000 8GB, 32GB RAM, i9-12950HX)
**Target:** Production-grade personal inference server for 2-5 users
**Philosophy:** Private, cost-effective alternative to cloud APIs using 2026 technology

---

## Executive Summary

Transform your ThinkPad P16 into a **personal OpenRouter** - a production-grade inference gateway that leverages January 2026's best local models and techniques. This plan modernizes RheaRouter beyond its November 2025 benchmarks, incorporating:

- **Nemotron-3-Nano 30B** (MoE, Dec 2025) - 30B params, only 3B active
- **DeepSeek R1 8B** (Jan 2025) - Advanced reasoning
- **Mixture-of-Agents (MoA)** - 2025 research showing better quality than GPT-4
- **Speculative decoding** - 1.11x-2.23x speedup
- **Smart production features** - Rate limiting, retries, observability

**Core Principle:** Start with pragmatic production features, architect for easy enhancement.

---

## What's Changed Since November 2025

### Your Original Benchmarks (Nov 2025)
- Tested: MiniCPM-V 8B, LLaVA 7B
- Finding: MiniCPM-V superior for OCR (95% accuracy)
- Focus: Ensemble consensus for vision tasks

### What's New in 2026
1. **Nemotron-3-Nano 30B** (Dec 2025) - Game-changer MoE model
   - 128 experts, top-6 routing + 2 shared experts
   - Fits in 6-8GB VRAM with Q4 quantization
   - 30B performance at 3B active params cost

2. **DeepSeek R1 Distilled** (Jan 2025) - Reasoning specialist
   - 68.5 tokens/sec on similar hardware
   - Excellent for complex queries

3. **MoA Research** (2025) - Layered multi-model architecture
   - Beats GPT-4 using only open models
   - Perfect for your use case

4. **Speculative Decoding** (2025) - Collaborative speculation
   - Use small model (draft) + large model (verify)
   - 1.11x-2.23x speedup without quality loss

**Recommendation:** Keep your vision ensemble work, add modern text/reasoning capabilities.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     RheaRouter API Server                       │
│                  (FastAPI + OpenAI-compatible)                  │
├─────────────────────────────────────────────────────────────────┤
│  Middleware Stack                                               │
│  ├─ Request ID + Structured Logging (JSON)                     │
│  ├─ Token Bucket Rate Limiter (in-memory, 60 req/min)          │
│  ├─ VRAM Flow Valve (1 vision slot, 2 text slots)              │
│  ├─ Prometheus Metrics                                          │
│  └─ Error Handler + Retry Logic (exponential backoff)          │
├─────────────────────────────────────────────────────────────────┤
│  Intelligent Router                                             │
│  ├─ Request Type Detection (vision vs text vs reasoning)       │
│  ├─ Model Selection (semantic routing)                         │
│  ├─ Fallback Strategy (primary → backup → 503)                 │
│  └─ MoA Orchestration (when needed)                            │
├─────────────────────────────────────────────────────────────────┤
│  Backend Layer                                                  │
│  ├─ Ollama Backend (primary)                                   │
│  ├─ Ensemble OCR (existing, opt-in)                            │
│  ├─ MoA Engine (new)                                           │
│  └─ Speculative Decoder (new)                                  │
├─────────────────────────────────────────────────────────────────┤
│  Persistence & Observability                                    │
│  ├─ SQLite (request/response logs, analytics)                  │
│  ├─ Prometheus Metrics Export (/metrics)                       │
│  ├─ Health Checks (/health/live, /health/ready)                │
│  └─ Status Dashboard (/status)                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Ollama Backend (11434)                       │
│                                                                 │
│  Vision Models:              Text Models:                       │
│  ├─ qwen2.5vl:7b (primary)  ├─ nemotron-3-nano:30b-a3b (MoE) │
│  ├─ minicpm-v:8b (OCR)      ├─ deepseek-r1:8b (reasoning)     │
│  └─ llava:7b (draft)        ├─ qwen3:8b (math)                │
│                              └─ llama3.1:8b (general)           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Model Strategy (2026 Optimized)

### Vision Models (Keep Your Existing Work)
| Model | VRAM | Use Case | Performance |
|-------|------|----------|-------------|
| **qwen2.5vl:7b** | 5.5GB | Primary vision (OCR, understanding) | 95% accuracy |
| **minicpm-v:8b** | 5.9GB | OCR ensemble (opt-in) | Tested in Nov 2025 |
| **llava:7b** | 4.7GB | Draft model for speculative decoding | Fast |

**Your Nov 2025 finding still holds:** Single Qwen2.5-VL beats ensemble for accuracy. Use ensemble as opt-in plugin for experimentation.

### Text Models (NEW - 2026 Additions)
| Model | VRAM | Use Case | Status |
|-------|------|----------|--------|
| **nemotron-3-nano:30b-a3b** | 6-8GB (Q4) | MoE powerhouse, complex tasks | **Add this** |
| **deepseek-r1:8b** | 6.2GB (Q4) | Reasoning, logic | **Add this** |
| **qwen3:8b** | 6-7GB (Q4) | Math, analytical | Already have |
| **llama3.1:8b** | 4.5GB (Q4) | General chat, fast | Already have |

### Routing Decision Matrix

```python
if has_image:
    if "extract text" in prompt or "read" in prompt:
        use qwen2.5vl:7b  # Best OCR (95% accuracy)
    else:
        use qwen2.5vl:7b  # Best vision understanding

elif requires_reasoning:  # Complex logic, math, multi-step
    if complexity == "high":
        use MoA([deepseek-r1:8b, qwen3:8b, nemotron-3-nano:30b])  # Debate
    else:
        use deepseek-r1:8b  # Single reasoning model

elif requires_coding:
    use nemotron-3-nano:30b-a3b  # Excellent for code

else:  # General completion
    use llama3.1:8b  # Fast, efficient
```

---

## Production Features (Pragmatic Stack)

### 1. Rate Limiting - Token Bucket (In-Memory)

**No Redis needed for 100-500 req/day**

```python
class FlowValveRateLimiter:
    """
    Two-tier token bucket:
    - Global: 60 req/min (burst: 10)
    - Per-client: 20 req/min (burst: 5)

    In-memory, thread-safe, O(1) operations.
    Upgrade to Redis if traffic > 5K req/day.
    """
```

**VRAM-Adaptive Rate Limiting:**
```python
if vram_usage > 90%:
    reduce_rate_to(30)  # req/min
elif vram_usage > 75%:
    reduce_rate_to(45)
else:
    normal_rate(60)
```

### 2. Intelligent Retry Logic

**Model-specific backoff strategies:**

| Failure Type | Max Attempts | Strategy | Backoff |
|--------------|--------------|----------|---------|
| Connection error | 5 | Exponential + jitter | 2s, 4s, 8s, 16s, 32s |
| Model loading | 2 | Linear | 5s, 10s |
| Inference timeout | 3 | Exponential | 10s, 20s, 40s |
| 4xx errors | 0 | No retry | - |

**Graceful degradation:**
1. Primary model fails → Retry with backoff
2. Still failing → Try fallback model
3. All fail → 503 with `Retry-After` header

### 3. Structured Logging (JSON, Minimal Deps)

**Library:** Python `logging` + `python-json-logger` (no ELK stack needed)

```json
{
  "timestamp": "2026-02-04T20:15:23.456Z",
  "level": "info",
  "event": "inference_completed",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "model": "nemotron-3-nano:30b-a3b",
  "technique": "moa_debate",
  "duration_ms": 3241,
  "vram_mb": 7800,
  "success": true
}
```

**What to log:**
- ✅ Request metadata (model, duration, tokens)
- ✅ Errors with full context
- ✅ VRAM pressure warnings (>90%)
- ❌ Full request/response bodies (privacy)
- ❌ Verbose success messages (noise)

### 4. Observability (Prometheus + Grafana)

**Metrics that matter:**
```
# Request metrics
rhearouter_requests_total{model, endpoint, status}
rhearouter_request_duration_seconds{model, quantile}
rhearouter_active_requests{model}

# VRAM metrics (from nvidia-smi exporter)
rhearouter_vram_used_mb
rhearouter_vram_utilization_percent
rhearouter_model_swap_total

# MoA metrics
rhearouter_moa_layers{strategy}
rhearouter_moa_quality_improvement{baseline_model}

# Error tracking
rhearouter_errors_total{type, model}
```

**Dashboard focus:**
- System health (success rate, latency p95, VRAM %)
- Model performance (which models used, swap frequency)
- GPU health (temp, power, utilization)

**Resource overhead:** ~600MB RAM, acceptable on 32GB system

### 5. Request Persistence (SQLite)

**Why SQLite over PostgreSQL:**
- Zero maintenance (embedded)
- Sufficient for 500 req/day (handles 10K+ easily)
- Single file backup
- 30-day retention = ~165MB disk

**Schema:**
```sql
CREATE TABLE requests (
    id TEXT PRIMARY KEY,
    timestamp REAL NOT NULL,
    endpoint TEXT NOT NULL,
    model_requested TEXT,
    technique_used TEXT,  -- single, moa_debate, ensemble_ocr
    models_used TEXT,     -- JSON array
    duration_ms REAL,
    tokens_generated INTEGER,
    vram_peak_mb INTEGER,
    error_type TEXT,
    trace_id TEXT
);
```

**Analytics queries:**
```sql
-- Model usage stats (last 7 days)
SELECT model, COUNT(*), AVG(duration_ms)
FROM requests
WHERE timestamp >= datetime('now', '-7 days')
GROUP BY model;

-- MoA effectiveness
SELECT technique_used, AVG(tokens_generated), AVG(duration_ms)
FROM requests
WHERE technique_used LIKE 'moa_%'
GROUP BY technique_used;
```

---

## Advanced Features (2026 Techniques)

### 1. Mixture-of-Agents (MoA)

**Research finding:** MoA using open models beats GPT-4 (65.1% vs 57.5% on AlpacaEval 2.0)

**Implementation:**

```python
class MoAEngine:
    """
    Layered multi-agent architecture.

    Layer 1: Multiple specialist models generate responses
    Layer 2: Aggregator model synthesizes best answer
    """

    async def debate_strategy(self, prompt: str) -> str:
        # Layer 1: Get diverse perspectives
        responses = await asyncio.gather(
            self.infer("deepseek-r1:8b", prompt),      # Reasoning
            self.infer("qwen3:8b", prompt),            # Math
            self.infer("nemotron-3-nano:30b", prompt)  # General
        )

        # Layer 2: Aggregator synthesizes
        aggregation_prompt = f"""
        Question: {prompt}

        Expert 1 (Reasoning): {responses[0]}
        Expert 2 (Math): {responses[1]}
        Expert 3 (General): {responses[2]}

        Synthesize the best answer considering all perspectives.
        """

        return await self.infer("nemotron-3-nano:30b", aggregation_prompt)
```

**When to use:**
- User explicitly requests MoA (`moa_strategy` parameter)
- High-complexity queries (detected by keyword analysis)
- Quality over speed scenarios

**Cost:** 3-4x latency of single model, but higher quality

### 2. Speculative Decoding

**Research finding:** 1.11x-2.23x speedup without quality loss

**Implementation:**

```python
class SpeculativeDecoder:
    """
    Use small draft model + large verifier.

    Draft (llava:7b) generates tokens quickly.
    Verifier (nemotron-3-nano:30b) accepts/rejects in parallel.
    """

    async def decode(self, prompt: str) -> str:
        draft_tokens = []
        verified_tokens = []

        while not_done:
            # Draft model generates 5 tokens quickly
            draft = await self.draft_model.generate(prompt, max_tokens=5)
            draft_tokens.extend(draft)

            # Verifier checks in parallel
            verified = await self.verifier_model.verify(prompt, draft_tokens)

            if verified:
                verified_tokens.extend(draft)
            else:
                # Reject, verifier generates correct token
                correct = await self.verifier_model.generate_one(prompt)
                verified_tokens.append(correct)
                draft_tokens = verified_tokens  # Reset

        return verified_tokens
```

**Use cases:**
- Long-form generation (articles, code)
- When latency matters more than throughput

### 3. Dynamic Model Selection

**Semantic routing with embeddings:**

```python
class SemanticRouter:
    """
    Route based on prompt semantics, not just keywords.

    Uses small embedding model to classify request type.
    """

    def route(self, prompt: str) -> str:
        embedding = self.embed_model.encode(prompt)

        # Cosine similarity to archetypes
        scores = {
            "vision": cosine(embedding, self.vision_archetype),
            "reasoning": cosine(embedding, self.reasoning_archetype),
            "coding": cosine(embedding, self.coding_archetype),
            "general": cosine(embedding, self.general_archetype)
        }

        best_match = max(scores, key=scores.get)
        return self.type_to_model[best_match]
```

**Fallback cascade:**
```
Primary model → Backup model → CPU-only mode → 503 error
```

---

## Configuration System

### Environment Variables (Primary)

```bash
# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
SERVER_WORKERS=1  # Single worker (VRAM constraint)

# Ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_TIMEOUT=120

# Rate Limiting
RATE_LIMIT_GLOBAL=60  # req/min
RATE_LIMIT_CLIENT=20  # req/min per client
RATE_LIMIT_VRAM_ADAPTIVE=true

# VRAM Management
VRAM_LIMIT_MB=8192
MODEL_SWAP_COOLDOWN=5.0
VISION_SLOTS=1  # Concurrent vision requests
TEXT_SLOTS=2    # Concurrent text requests

# Retry
RETRY_MAX_ATTEMPTS=3
RETRY_BACKOFF_MULTIPLIER=2

# Features (enable/disable)
FEATURE_AUTH=true
FEATURE_RATE_LIMITING=true
FEATURE_ENSEMBLE_OCR=false  # Opt-in (single model is better)
FEATURE_MOA=true
FEATURE_SPECULATIVE_DECODING=false  # Opt-in

# API Keys (comma-separated)
API_KEYS=your-key-1,your-key-2,your-key-3

# Observability
LOG_LEVEL=INFO
METRICS_ENABLED=true
DB_RETENTION_DAYS=30
```

### YAML Config (Optional)

```yaml
# config/production.yaml

models:
  vision:
    primary: qwen2.5vl:7b
    fallback: minicpm-v:8b
    draft: llava:7b  # For speculative decoding

  text:
    primary: nemotron-3-nano:30b-a3b
    reasoning: deepseek-r1:8b
    math: qwen3:8b
    general: llama3.1:8b

routing:
  strategy: semantic  # or "keyword"
  fallback_enabled: true

moa:
  enabled: true
  default_strategy: debate
  layer1_models:
    - deepseek-r1:8b
    - qwen3:8b
    - nemotron-3-nano:30b-a3b
  layer2_model: nemotron-3-nano:30b-a3b

ensemble_ocr:  # Your existing work
  enabled: false  # Disabled by default (single model is better)
  default_technique: escalation_chain
  models:
    - qwen2.5vl:7b
    - minicpm-v:8b
    - llava:7b
```

---

## Deployment Options

### Option 1: Systemd (Recommended for Production)

**Advantages:**
- Native performance (no container overhead)
- Direct GPU access
- Managed by systemd (auto-restart)
- Logs via journalctl

**Installation:**

```bash
# 1. Create service user
sudo useradd -r -s /bin/false rhearouter

# 2. Create directories
sudo mkdir -p /opt/rhearouter
sudo mkdir -p /etc/rhearouter
sudo mkdir -p /var/lib/rhearouter  # SQLite, models
sudo mkdir -p /var/log/rhearouter

# 3. Set permissions
sudo chown rhearouter:rhearouter /var/lib/rhearouter /var/log/rhearouter

# 4. Install app
cd /opt/rhearouter
python3 -m venv venv
venv/bin/pip install -e .

# 5. Configure
sudo cp deployment/rhearouter.env /etc/rhearouter/
sudo cp deployment/rhearouter.service /etc/systemd/system/

# 6. Enable and start
sudo systemctl daemon-reload
sudo systemctl enable rhearouter
sudo systemctl start rhearouter

# 7. Check status
sudo systemctl status rhearouter
curl http://localhost:8000/health
```

**Service file:**

```ini
# /etc/systemd/system/rhearouter.service
[Unit]
Description=RheaRouter Personal Inference Server
After=network.target ollama.service
Wants=ollama.service

[Service]
Type=simple
User=rhearouter
Group=rhearouter
WorkingDirectory=/opt/rhearouter
EnvironmentFile=/etc/rhearouter/rhearouter.env

ExecStart=/opt/rhearouter/venv/bin/uvicorn \
    server.main:app \
    --host ${SERVER_HOST} \
    --port ${SERVER_PORT} \
    --workers ${SERVER_WORKERS}

Restart=always
RestartSec=10s

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/rhearouter /var/log/rhearouter

[Install]
WantedBy=multi-user.target
```

### Option 2: Docker Compose (Development + Observability Stack)

**Advantages:**
- Includes full observability (Prometheus, Grafana, Jaeger)
- Isolated environment
- Easy to update (rebuild image)
- Portable configuration

**Stack:**

```yaml
# docker-compose.yml

version: '3.8'

services:
  rhearouter:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OLLAMA_URL=http://host.docker.internal:11434
      - METRICS_ENABLED=true
    volumes:
      - ./data:/var/lib/rhearouter
      - ./logs:/var/log/rhearouter
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./observability/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=changeme
    volumes:
      - ./observability/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - grafana-data:/var/lib/grafana

  nvidia-exporter:
    image: utkuozdemir/nvidia_gpu_exporter:latest
    ports:
      - "9835:9835"
    runtime: nvidia

volumes:
  prometheus-data:
  grafana-data:
```

**Start stack:**
```bash
docker-compose up -d

# Access
# API: http://localhost:8000
# Grafana: http://localhost:3000 (admin/changeme)
# Prometheus: http://localhost:9090
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Goal:** Production API server with core features

**Deliverables:**
1. FastAPI app structure
   - `src/api/main.py` - App initialization, middleware
   - `src/api/routes.py` - OpenAI-compatible endpoints
   - `src/api/models.py` - Pydantic schemas

2. Middleware stack
   - Request ID + structured logging
   - Token bucket rate limiter
   - VRAM flow valve
   - Error handler + retry logic

3. Ollama backend adapter
   - `src/core/backends/ollama.py` - API wrapper
   - Request translation (OpenAI → Ollama format)
   - Response normalization

4. Configuration system
   - Environment variables
   - YAML config (optional)
   - Feature flags

5. Health checks
   - `/health/live` - Liveness probe
   - `/health/ready` - Readiness probe
   - `/status` - Detailed status

**Testing:**
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1:8b",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

**Estimated LOC:** ~800 lines of new code

### Phase 2: Model Management (Week 3)

**Goal:** Intelligent routing + modern models

**Deliverables:**
1. Install 2026 models
   ```bash
   ollama pull nemotron-3-nano:30b-a3b-q4_K_M
   ollama pull deepseek-r1:8b
   ollama pull qwen3:8b
   ```

2. Model router
   - `src/core/router.py` - Intelligent routing
   - Request type detection (vision vs text vs reasoning)
   - Model selection logic
   - Fallback cascade

3. VRAM-aware scheduling
   - Integrate existing `ModelManager` from ensemble code
   - Track loaded models
   - Swap orchestration with cooldown

4. SQLite persistence
   - `src/core/persistence.py` - Request logging
   - Analytics queries
   - Auto-cleanup (30-day retention)

**Testing:**
```bash
# Vision request
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer your-key" \
  -d '{
    "model": "qwen2.5vl:7b",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "What's in this image?"},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
      ]
    }]
  }'

# Auto-routing (should select deepseek-r1:8b for reasoning)
curl -X POST http://localhost:8000/v1/chat/completions \
  -d '{
    "messages": [{"role": "user", "content": "Solve: If x^2 = 16, what is x?"}]
  }'
```

**Estimated LOC:** ~500 lines

### Phase 3: Advanced Features (Week 4-5)

**Goal:** MoA + speculative decoding

**Deliverables:**
1. MoA engine
   - `src/core/moa.py` - Mixture-of-Agents implementation
   - Debate strategy (Layer 1: specialists, Layer 2: aggregator)
   - Quality metrics tracking

2. Speculative decoding (optional)
   - `src/core/speculative.py` - Draft + verify workflow
   - Enable via feature flag

3. Wrap existing ensemble OCR
   - `src/plugins/ensemble_ocr.py` - Plugin wrapper
   - Integrate with your Nov 2025 code
   - Opt-in via API parameter

**API usage:**

```bash
# MoA for complex reasoning
curl -X POST http://localhost:8000/v1/chat/completions \
  -d '{
    "messages": [{"role": "user", "content": "Explain quantum entanglement"}],
    "moa_strategy": "debate"
  }'

# Ensemble OCR (opt-in)
curl -X POST http://localhost:8000/v1/images/analyze \
  -d '{
    "image": "base64...",
    "task": "ocr",
    "ensemble_technique": "weighted_voting"
  }'
```

**Estimated LOC:** ~600 lines

### Phase 4: Observability (Week 6)

**Goal:** Production monitoring

**Deliverables:**
1. Prometheus metrics
   - `src/observability/metrics.py` - Metrics collection
   - `/metrics` endpoint (Prometheus text format)
   - GPU metrics integration (nvidia-smi exporter)

2. Grafana dashboards
   - System overview (health, latency, VRAM)
   - Model performance (usage, swap frequency)
   - Error tracking

3. Alerting rules
   - VRAM >90% for 5m
   - GPU temp >80°C
   - Error rate >10%
   - P95 latency >30s

4. Deployment automation
   - Docker Compose stack (full observability)
   - Systemd service files
   - Backup scripts (SQLite, config)

**Monitoring:**
```bash
# Prometheus
curl http://localhost:9090/metrics

# Grafana
open http://localhost:3000

# SQLite analytics
sqlite3 /var/lib/rhearouter/requests.db "
  SELECT model, COUNT(*), AVG(duration_ms)
  FROM requests
  WHERE timestamp >= datetime('now', '-24 hours')
  GROUP BY model;
"
```

**Estimated LOC:** ~400 lines

---

## Critical Files & Integration Points

### New Files to Create

**Phase 1 (Core API):**
1. `src/api/main.py` (150 LOC) - FastAPI app, middleware registration
2. `src/api/routes.py` (200 LOC) - OpenAI-compatible endpoints
3. `src/api/models.py` (100 LOC) - Pydantic request/response schemas
4. `src/core/backends/ollama.py` (150 LOC) - Ollama API adapter
5. `src/middleware/rate_limit.py` (200 LOC) - Token bucket, VRAM flow valve
6. `src/middleware/logging.py` (100 LOC) - Structured logging
7. `src/middleware/retry.py` (100 LOC) - Retry logic with backoff
8. `src/core/config.py` (150 LOC) - Configuration management

**Phase 2 (Routing):**
9. `src/core/router.py` (250 LOC) - Intelligent model routing
10. `src/core/persistence.py` (150 LOC) - SQLite request logging

**Phase 3 (Advanced):**
11. `src/core/moa.py` (300 LOC) - Mixture-of-Agents engine
12. `src/core/speculative.py` (200 LOC) - Speculative decoding
13. `src/plugins/ensemble_ocr.py` (100 LOC) - Wrapper for existing ensemble

**Phase 4 (Observability):**
14. `src/observability/metrics.py` (200 LOC) - Prometheus metrics
15. `src/observability/dashboards/*.json` - Grafana dashboards

**Total new code:** ~2,400 LOC

### Existing Files to Integrate (Read-Only)

**These files already work, reuse them:**

1. **`src/ensemble/facade.py`** (244 LOC)
   - Main ensemble OCR entry point
   - Already implements 3 consensus techniques
   - **Integration:** Wrap as plugin, call from router when user opts in

2. **`src/ensemble/model_manager.py`** (145 LOC)
   - VRAM-aware model loading
   - Swap cooldown logic
   - **Integration:** Use directly in VRAM flow valve middleware

3. **`src/ensemble/llm_agent.py`** (191 LOC)
   - Ollama API wrapper
   - Image encoding, confidence estimation
   - **Integration:** Reference for building `ollama.py` backend adapter

4. **`src/ensemble/consensus/escalation_chain.py`** (205 LOC)
   - Best ensemble technique per your benchmarks
   - Early exit optimization
   - **Integration:** Pattern for MoA implementation

5. **`benchmark/test8_ensemble/ensemble_benchmark.py`**
   - Benchmarking patterns
   - **Integration:** Use for testing new MoA/speculative features

**Key principle:** Don't rewrite what works. Wrap and extend.

---

## Dependencies (Minimal Stack)

```txt
# Core framework
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Already in use (ensemble code)
requests==2.31.0
Pillow==10.2.0
numpy==1.26.0

# New dependencies
tenacity==8.2.3              # Retry logic
python-json-logger==2.0.7    # Structured logging
apscheduler==3.10.4          # Cleanup jobs
prometheus-client==0.19.0    # Metrics

# Optional
pyyaml==6.0.1               # YAML config
opentelemetry-sdk==1.21.0   # Tracing (if using Jaeger)
```

**Total: 10 core packages** (no Redis, no PostgreSQL, no Elasticsearch)

**Resource overhead:**
- API server: ~150MB RAM
- Observability stack (Docker): ~600MB RAM
- Total: ~750MB RAM (acceptable on 32GB system)

---

## Performance Expectations (Based on Your Hardware)

### Latency Estimates

| Request Type | Model | Expected Latency | VRAM |
|--------------|-------|------------------|------|
| Vision OCR (single) | qwen2.5vl:7b | 3-5s | 5.5GB |
| Vision OCR (ensemble) | 3 models | 15-20s | 5-6GB |
| Text completion | llama3.1:8b | 1-2s | 4.5GB |
| Text reasoning | deepseek-r1:8b | 2-3s | 6.2GB |
| Text MoE | nemotron-3-nano:30b | 5-8s | 7GB |
| MoA (3 models) | 3x infer + aggregate | 10-15s | 6-7GB |
| Speculative decode | draft + verify | 3-6s (1.5-2x speedup) | 7-8GB |

### Throughput

**Sequential processing (1 worker, VRAM constraint):**
- Vision: 10-20 req/hour
- Text: 100-200 req/hour
- Mixed: 30-60 req/hour

**Your target (100-500 req/day):**
- Average: 4-20 req/hour ✅ Well within capacity
- Peak: 30-50 req/hour ✅ Manageable with queueing

### VRAM Management

**Model sizes (Q4 quantization):**
- Vision models: 4.7-5.9 GB
- Text 8B models: 4.5-6.2 GB
- Nemotron-3-Nano 30B MoE: 6-8 GB

**Strategy:**
- Load one model at a time (8GB constraint)
- 5-second cooldown between swaps
- Queue requests when VRAM busy
- Swap only when necessary (minimize thrashing)

---

## Cost Analysis

### Cloud API Costs (What You're Replacing)

**Typical usage (500 req/day, mixed vision + text):**
- Vision API (GPT-4V): $0.01-0.03 per request = $5-15/day
- Text API (GPT-4): $0.002-0.01 per request = $1-5/day
- **Total: $180-600/month**

### Local Inference Costs

**Electricity:**
- Power: ~150W average (GPU + CPU)
- Usage: 8 hours/day
- Cost: $0.12/kWh (US average)
- **Total: ~$4.40/month**

**ROI:** Save $175-595/month vs cloud APIs
**Payback period:** Immediate (using existing hardware)

### Privacy Benefits

**Priceless:**
- ✅ Data never leaves your network
- ✅ No API key exposure
- ✅ Offline operation
- ✅ Full audit trail
- ✅ Compliance-ready (GDPR, HIPAA if needed)

---

## Risk Mitigation

### Known Limitations

1. **VRAM constraint (8GB)**
   - Mitigation: Sequential processing, VRAM flow valve
   - Can't run models >15B efficiently on GPU alone
   - Workaround: Hybrid GPU/CPU for larger models

2. **Disk space (root partition 98% full)**
   - **CRITICAL:** Free up 10GB before starting
   - Cleanup commands:
     ```bash
     sudo apt clean
     sudo apt autoremove --purge
     sudo journalctl --vacuum-size=500M
     snap list --all | awk '/disabled/{print $1, $3}' | \
       while read snap rev; do sudo snap remove "$snap" --revision="$rev"; done
     ```

3. **Single machine (no redundancy)**
   - Mitigation: Systemd auto-restart
   - Backup: Daily SQLite backup to `/home` partition
   - Monitoring: Alerting for failures

4. **Thermal management**
   - Mitigation: Monitor GPU temp, alert at 80°C
   - Recommendation: Laptop cooling pad for 24/7 operation

### Disaster Recovery

**Backup strategy:**
```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR=/home/djshanklin/backups/rhearouter
DATE=$(date +%Y%m%d)

# Backup SQLite
cp /var/lib/rhearouter/requests.db $BACKUP_DIR/requests-$DATE.db

# Backup config
cp /etc/rhearouter/rhearouter.env $BACKUP_DIR/config-$DATE.env

# Keep 30 days
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
```

**Recovery:**
```bash
# Restore database
cp $BACKUP_DIR/requests-20260204.db /var/lib/rhearouter/requests.db
sudo systemctl restart rhearouter
```

---

## Security Considerations

### Authentication

**API Key based (simple, effective for 2-5 users):**

```python
@app.middleware("http")
async def auth_middleware(request, call_next):
    if request.url.path.startswith("/health"):
        return await call_next(request)  # Health checks public

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    token = auth_header.replace("Bearer ", "")
    if token not in config.api_keys:
        return JSONResponse(status_code=403, content={"error": "Forbidden"})

    return await call_next(request)
```

**Key management:**
```bash
# Generate keys
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Store in env
API_KEYS=key1,key2,key3
```

### Network Security

**Firewall rules:**
```bash
# Allow only local network
sudo ufw allow from 192.168.1.0/24 to any port 8000

# Or specific IPs
sudo ufw allow from 192.168.1.100 to any port 8000
```

**Reverse proxy (optional, for HTTPS):**
```nginx
# /etc/nginx/sites-available/rhearouter
server {
    listen 443 ssl;
    server_name rhearouter.local;

    ssl_certificate /etc/ssl/certs/rhearouter.crt;
    ssl_certificate_key /etc/ssl/private/rhearouter.key;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Data Privacy

**Request logging:**
- ❌ Don't log full request/response bodies
- ✅ Log metadata only (model, duration, tokens)
- ✅ Separate PII data (if needed)

**SQLite encryption (optional):**
```bash
# Install sqlcipher
sudo apt install sqlcipher

# Encrypt database
sqlcipher /var/lib/rhearouter/requests.db
  PRAGMA key = 'your-encryption-key';
  ATTACH DATABASE 'encrypted.db' AS encrypted KEY 'your-encryption-key';
  SELECT sqlcipher_export('encrypted');
```

---

## Success Metrics

### Week 1-2 (Foundation)
- ✅ API returns 200 for `/health`
- ✅ Single text completion works
- ✅ Rate limiting rejects at 61st request/min
- ✅ Logs in JSON format
- ✅ SQLite logging works

### Week 3 (Routing)
- ✅ Vision requests route to qwen2.5vl:7b
- ✅ Reasoning requests route to deepseek-r1:8b
- ✅ VRAM flow valve prevents thrashing
- ✅ Fallback works when primary fails
- ✅ Analytics query returns model usage

### Week 4-5 (Advanced)
- ✅ MoA debate returns synthesized answer
- ✅ MoA quality > single model (user evaluation)
- ✅ Ensemble OCR plugin works (opt-in)
- ✅ Speculative decoding shows speedup

### Week 6 (Production)
- ✅ Grafana dashboard shows metrics
- ✅ Alert fires when VRAM >90%
- ✅ Systemd service survives reboot
- ✅ Backup script runs daily
- ✅ Load test: 50 requests in 1 hour succeeds

**Final acceptance:** Your team uses RheaRouter instead of cloud APIs for 1 week.

---

## Next Steps (Immediate Actions)

### 1. Fix Critical Disk Space Issue

**Before anything else:**
```bash
# Check current usage
df -h /

# Clean up
sudo apt clean
sudo apt autoremove --purge
sudo journalctl --vacuum-size=500M

# Remove old snap versions
snap list --all | awk '/disabled/{print $1, $3}' | \
  while read snap rev; do sudo snap remove "$snap" --revision="$rev"; done

# Verify freed space (should have 10+ GB)
df -h /
```

### 2. Install 2026 Models

```bash
# Install Nemotron-3-Nano (game-changer MoE)
ollama pull nemotron-3-nano:30b-a3b-q4_K_M

# Install DeepSeek R1 (reasoning specialist)
ollama pull deepseek-r1:8b

# Verify
ollama list
```

### 3. Set Up Development Environment

```bash
cd /home/djshanklin/repos/rhearouter

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install base dependencies
pip install fastapi uvicorn[standard] pydantic pydantic-settings

# Create basic structure
mkdir -p src/api src/core src/middleware src/observability
```

### 4. Start Phase 1 Implementation

**Week 1 focus:**
1. Create `src/api/main.py` - FastAPI app skeleton
2. Add basic health check endpoint
3. Set up structured logging
4. Test with curl

**Week 2 focus:**
1. Implement rate limiting middleware
2. Add Ollama backend adapter
3. Create first OpenAI-compatible endpoint
4. Integration test with real models

---

## Conclusion

This plan transforms RheaRouter into a **modern, 2026-optimized personal inference server** by:

1. **Leveraging 2026 technology:**
   - Nemotron-3-Nano MoE (Dec 2025)
   - DeepSeek R1 reasoning (Jan 2025)
   - MoA multi-agent architecture (2025 research)
   - Speculative decoding (2025 optimization)

2. **Keeping what works:**
   - Your vision ensemble research (Nov 2025)
   - VRAM-aware model management
   - Proven benchmark patterns

3. **Adding production features:**
   - Rate limiting, retries, observability
   - SQLite persistence, health checks
   - Systemd + Docker deployment
   - Security (API keys, firewalls)

4. **Staying pragmatic:**
   - Minimal dependencies (no Redis, PostgreSQL, Elasticsearch)
   - Start simple, add complexity incrementally
   - Feature flags for experimental features
   - Clear phases with measurable success

**Core philosophy:** Self-hosted inference in 2026 is **private, cost-effective, and powerful** - this plan makes it production-ready.

**Estimated timeline:** 6 weeks to production-grade system
**Estimated effort:** 2,400 LOC new code + integration
**ROI:** $175-595/month savings vs cloud APIs
**Privacy:** Priceless

Ready to implement when you are.
