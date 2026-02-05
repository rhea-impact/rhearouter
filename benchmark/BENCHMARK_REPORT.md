# RheaRouter Vision Model Benchmark Report

**Date:** November 24, 2025
**Hardware:** NVIDIA RTX A2000 8GB, Intel i9-12950HX, 32GB RAM
**Ollama Version:** Latest

---

## Executive Summary

Both **MiniCPM-V 2.6 (8B)** and **LLaVA 7B** performed excellently on the RTX A2000 8GB GPU. Both models fit comfortably in VRAM and delivered responsive inference times suitable for production use.

| Metric | MiniCPM-V 8B | LLaVA 7B | Winner |
|--------|-------------|----------|--------|
| **Avg Response Time** | 5.63s | 4.46s | LLaVA |
| **Avg Words/Response** | 145 | 131 | MiniCPM-V |
| **Tokens/sec** | 44.0 | 44.6 | Tie |
| **VRAM Usage** | 5,947 MB | 5,725 MB | LLaVA |
| **Success Rate** | 100% | 100% | Tie |
| **Response Quality** | Excellent | Good | MiniCPM-V |

---

## Test Configuration

### Models Tested
1. **minicpm-v:8b** - OpenBMB's MiniCPM-V 2.6 (8.1B parameters, 5.5GB)
2. **llava:7b** - LLaVA 1.5 (7B parameters, 4.7GB)

### Test Images (5 diverse categories)
| Image | Category | Size | Description |
|-------|----------|------|-------------|
| 01_nature_ant.jpg | Macro/Nature | 31 KB | Close-up of ant on concrete |
| 02_diagram_dice.png | Digital/Graphic | 48 KB | Colorful 3D dice illustration |
| 03_wildlife_bird.jpg | Wildlife/Pet | 210 KB | Orange tabby cat portrait |
| 04_pet_cat.jpg | Pet/Outdoor | 88 KB | Fluffy cat resting on pavement |
| 05_art_monalisa.jpg | Art/Famous | 69 KB | Mona Lisa painting |

### Test Prompt
> "Describe this image in detail."

---

## Detailed Results

### MiniCPM-V 8B Performance

| Image | Time | Words | Tokens | Tok/s |
|-------|------|-------|--------|-------|
| Ant (nature) | 4.89s | 139 | 166 | 43.9 |
| Dice (diagram) | 5.47s | 156 | 180 | 45.1 |
| Cat portrait | 5.25s | 61 | 72 | 44.7 |
| Cat outdoor | 5.96s | 175 | 209 | 43.5 |
| Mona Lisa | 6.57s | 195 | 234 | 43.3 |
| **Average** | **5.63s** | **145** | **172** | **44.0** |

**Observations:**
- Consistently detailed responses with rich vocabulary
- Correctly identified the Mona Lisa and provided art history context
- Structured responses with bullet points for the ant anatomy
- Slightly slower due to longer response generation
- VRAM stable at 5,947 MB throughout

### LLaVA 7B Performance

| Image | Time | Words | Tokens | Tok/s |
|-------|------|-------|--------|-------|
| Ant (nature) | 2.86s | 97 | 125 | 44.8 |
| Dice (diagram) | 4.51s | 136 | 170 | 44.7 |
| Cat portrait | 4.92s | 134 | 187 | 44.6 |
| Cat outdoor | 6.15s | 180 | 240 | 44.3 |
| Mona Lisa | 3.85s | 108 | 141 | 44.8 |
| **Average** | **4.46s** | **131** | **173** | **44.6** |

**Observations:**
- Faster response times overall (~21% faster)
- Good descriptions but occasionally added hallucinated details
- Lower VRAM footprint (5,723-5,725 MB)
- More concise responses
- Mona Lisa response included incorrect details (black hat, fan)

---

## Response Quality Analysis

### Accuracy Assessment

| Image | MiniCPM-V 8B | LLaVA 7B |
|-------|-------------|----------|
| **Ant** | Accurate anatomy description, correct surface identification | Hallucinated "wood in mouth" and "bottle in background" |
| **Dice** | Correctly identified 4 dice, accurate colors | Said "six dice" and added non-existent text |
| **Cat Portrait** | Accurate - orange tabby, yellow eyes | Accurate - same correct identification |
| **Cat Outdoor** | Accurate - white/brown with stripes | Accurate - gray and white with collar |
| **Mona Lisa** | Excellent - identified artist, described smile, landscape | Hallucinated "black hat" and "fan" |

**Quality Winner: MiniCPM-V 8B** - More accurate, fewer hallucinations

---

## VRAM Analysis

```
Total Available: 8,192 MB

MiniCPM-V 8B:
├── Model Load: ~5,500 MB
├── Inference Peak: 5,947 MB
└── Headroom: 2,245 MB (27%)

LLaVA 7B:
├── Model Load: ~4,700 MB
├── Inference Peak: 5,725 MB
└── Headroom: 2,467 MB (30%)
```

Both models leave sufficient headroom for:
- Concurrent requests (limited)
- System overhead
- Image preprocessing

---

## Recommendations

### For RheaRouter Production Use

1. **Primary Model: MiniCPM-V 8B**
   - Better accuracy and response quality
   - Excellent OCR capabilities (not tested here)
   - Worth the extra ~200MB VRAM and ~1s latency

2. **Fallback/Fast Model: LLaVA 7B**
   - 21% faster responses
   - Lower VRAM for memory-constrained scenarios
   - Good enough for simple image classification tasks

### Performance Expectations

| Use Case | Expected Latency | Throughput |
|----------|-----------------|------------|
| Single image description | 4-7 seconds | ~10 req/min |
| Quick classification | 2-4 seconds | ~15 req/min |
| Batch processing | N/A (sequential) | ~10 images/min |

---

## Hardware Verdict

The **RTX A2000 8GB** is **SUITABLE** for RheaRouter vision inference:

- Both top vision models run comfortably
- ~44 tokens/second is acceptable for interactive use
- 4-6 second response times are reasonable
- VRAM headroom allows for API overhead
- No OOM errors observed

**Limitation:** Cannot run both models simultaneously - must swap between them.

---

## Files Generated

- `benchmark/vision_benchmark.py` - Reusable benchmark script
- `benchmark/results/benchmark_20251124_223540.json` - Raw results data
- `benchmark/images/` - Test image set

---

*Report generated by RheaRouter Benchmark Suite*
