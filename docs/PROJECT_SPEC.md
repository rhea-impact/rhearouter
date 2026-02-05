# RheaRouter - Self-Hosted Inference Server

## Overview

RheaRouter is a self-hosted inference gateway that provides OpenRouter-like functionality on local infrastructure. It enables the company to run multi-modal and text-based AI inference without relying on external paid APIs.

## Goals

1. **Cost Elimination** - Zero per-token fees by running inference locally
2. **Data Privacy** - All requests and responses stay on company infrastructure
3. **Full Control** - Choose which models to deploy, how to configure them, and when to update
4. **Low Latency** - Eliminate network round-trips to external providers
5. **OpenAI-Compatible API** - Drop-in replacement for existing integrations

## System Hardware

| Component | Specification |
|-----------|---------------|
| **GPU** | NVIDIA RTX A2000 8GB Laptop GPU |
| **VRAM** | 8 GB GDDR6 |
| **CPU** | Intel Core i9-12950HX (16 cores, 24 threads, up to 5.0 GHz) |
| **RAM** | 32 GB DDR5 |
| **CUDA** | Version 13.0 |
| **Driver** | 580.95.05 |

## Hardware Constraints & Capabilities

### What 8GB VRAM Can Run

| Model Type | Examples | Feasibility |
|------------|----------|-------------|
| 7B parameter LLMs (4-bit) | Llama 3.1 7B, Mistral 7B, Qwen 2.5 7B | Excellent |
| 7B parameter LLMs (8-bit) | Same models at higher precision | Good |
| 13B parameter LLMs (4-bit) | Llama 2 13B, CodeLlama 13B | Good (tight fit) |
| Vision-Language Models | LLaVA 7B, Qwen-VL, MiniCPM-V | Good |
| Image understanding | CLIP, BLIP-2 | Excellent |
| Embedding models | BGE, E5, Nomic | Excellent |

### What Won't Fit

- 70B+ parameter models (even quantized)
- Large vision models like LLaVA-34B
- Multiple large models simultaneously

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      RheaRouter API                         │
│                   (FastAPI / Flask)                         │
│                                                             │
│  Endpoints:                                                 │
│  - POST /v1/chat/completions    (OpenAI-compatible)        │
│  - POST /v1/completions         (Legacy completions)        │
│  - POST /v1/embeddings          (Text embeddings)           │
│  - GET  /v1/models              (List available models)     │
│  - POST /v1/images/analyze      (Vision/multimodal)         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Inference Backend                        │
│                                                             │
│  Options:                                                   │
│  - Ollama (easiest setup, good performance)                │
│  - llama.cpp server (lightweight, efficient)               │
│  - vLLM (best throughput, more VRAM hungry)                │
│  - TGI (Hugging Face, production-ready)                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    NVIDIA RTX A2000                         │
│                      8GB VRAM                               │
│                    CUDA 13.0                                │
└─────────────────────────────────────────────────────────────┘
```

## Recommended Stack

Given the 8GB VRAM constraint, the recommended stack is:

### Backend: Ollama
- **Why**: Simple setup, automatic model management, good quantization support, already optimized for consumer GPUs
- **Alternative**: llama.cpp server for more control

### API Layer: FastAPI wrapper
- Translates OpenRouter/OpenAI format to backend
- Handles authentication, rate limiting, logging
- Provides unified interface regardless of backend

### Models to Deploy

1. **Primary LLM**: Llama 3.1 8B (Q4_K_M quantization) - ~5GB VRAM
2. **Vision Model**: LLaVA 7B or MiniCPM-V 2.6 - ~5GB VRAM
3. **Embeddings**: nomic-embed-text - ~300MB VRAM

*Note: Run one large model at a time, swap as needed*

## API Compatibility

RheaRouter will implement OpenAI-compatible endpoints:

```bash
# Text completion
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer $RHEA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1:8b",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# Vision/Multimodal
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer $RHEA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llava:7b",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "What is in this image?"},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
      ]
    }]
  }'
```

## Phases

### Phase 1: Hardware Validation (Current)
- [ ] Run GPU benchmarks
- [ ] Test VRAM limits
- [ ] Verify CUDA functionality
- [ ] Test image processing speed

### Phase 2: Backend Setup
- [ ] Install Ollama or chosen backend
- [ ] Download and test models
- [ ] Verify inference works

### Phase 3: API Development
- [ ] Create FastAPI server
- [ ] Implement OpenAI-compatible endpoints
- [ ] Add authentication
- [ ] Add request logging

### Phase 4: Production Hardening
- [ ] Add systemd service
- [ ] Configure firewall/networking
- [ ] Set up monitoring
- [ ] Performance tuning

## Security Considerations

- API key authentication required
- Rate limiting to prevent abuse
- Request/response logging for audit
- Network isolation (internal network only recommended)
- No sensitive data in logs

## Success Criteria

1. Can serve text inference requests with <2s latency for typical queries
2. Can process image + text multimodal requests
3. API is compatible with OpenAI client libraries
4. Server runs stable under continuous load
5. VRAM usage stays within 8GB limit
