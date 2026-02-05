# Extended Benchmark Analysis - 10 Diverse Images

**Date:** November 24, 2025
**Images Tested:** 10 diverse categories
**Prompts per Image:** 3 (describe, identify, context)
**Total Tests:** 60 (30 per model)

---

## Test Results Summary

### Overall Scores

| Model | Avg Score | Avg Time | Avg Words | Tokens/sec |
|-------|-----------|----------|-----------|------------|
| **MiniCPM-V 8B** | **68%** | 4.36s | 137 | 43.8 |
| **LLaVA 7B** | **56%** | 3.28s | 101 | 44.8 |

**Winner: MiniCPM-V 8B (+12% accuracy)**

---

## Category-by-Category Analysis

### Categories Where MiniCPM-V Dominates

| Category | MiniCPM-V | LLaVA | Gap |
|----------|-----------|-------|-----|
| **Art** | 88% | 68% | +20% |
| **Space** | 79% | 50% | +29% |
| **Landscape** | 77% | 53% | +24% |
| **Food** | 67% | 46% | +21% |
| **Wildlife** | 46% | 33% | +13% |

### Categories Where Performance is Close

| Category | MiniCPM-V | LLaVA | Gap |
|----------|-----------|-------|-----|
| Architecture | 67% | 58% | +9% |
| Landmark | 71% | 76% | -5% |
| Animals | 58% | 62% | -4% |
| Urban | 38% | 42% | -4% |

### Key Observations

#### 1. **Art Recognition is MiniCPM-V's Strength**
- Starry Night: 100% vs 78% (MiniCPM-V identified painter, period, and all visual elements)
- Great Wave: 88% vs 58% (MiniCPM-V named Hokusai correctly, LLaVA missed it)
- MiniCPM-V provides art historical context that LLaVA lacks

#### 2. **Space/Scientific Images Favor MiniCPM-V**
- Astronaut: 79% vs 50%
- MiniCPM-V correctly identified EVA context
- LLaVA gave shorter, less complete answers

#### 3. **Urban Images Challenged Both Models**
- Both scored poorly (38-42%) on urban street scene
- The Unsplash image was an NYC skyline, not a street-level view
- This reveals a mismatch between expected keywords and actual image content
- **Note:** This exposes a limitation in my test design, not the models

#### 4. **Wildlife Needs Improvement**
- Tiger: 46% (MiniCPM-V) vs 33% (LLaVA)
- Neither consistently mentioned "Bengal" or "feline"
- Both described stripes and habitat correctly

---

## Response Quality Analysis

### Response Length

| Model | Describe Avg | Identify Avg | Context Avg |
|-------|-------------|--------------|-------------|
| MiniCPM-V | 211 words | 56 words | 132 words |
| LLaVA | 147 words | 45 words | 98 words |

**MiniCPM-V produces 40% more detailed responses**

### Best Responses by Category

#### Art - Starry Night (MiniCPM-V: 100%)
> "This captivating painting captures the essence of Vincent van Gogh's iconic 'Starry Night'... The painting is executed in Van Gogh's distinctive post-impressionist style, characterized by bold brushstrokes and vivid color contrasts."

#### Landmark - Golden Gate (Both: 86%)
Both models excelled here, correctly identifying:
- Golden Gate Bridge
- San Francisco
- Suspension bridge design
- Bay location

#### Space - Astronaut (MiniCPM-V: 88% context)
> "The context of this image appears to depict a scene from space exploration, specifically an astronaut in orbit... This could be an EVA (Extra-Vehicular Activity) conducted by astronauts during space missions..."

---

## Response Time Analysis

### Fastest Responses (Identify prompt)

| Model | Fastest | Slowest | Avg |
|-------|---------|---------|-----|
| MiniCPM-V | 1.03s | 2.44s | 1.59s |
| LLaVA | 0.60s | 2.79s | 1.45s |

### Describe Prompt (Most Comprehensive)

| Model | Fastest | Slowest | Avg |
|-------|---------|---------|-----|
| MiniCPM-V | 4.23s | 11.12s | 6.52s |
| LLaVA | 2.81s | 7.70s | 4.97s |

**LLaVA is 24% faster but 40% less detailed**

---

## Failure Modes Identified

### Common Keyword Misses

1. **"Landmark"** - Both models describe famous places but rarely use the word "landmark"
2. **Technical Terms** - "feline", "suspension", "iron" often missed even when describing correct features
3. **Specific Names** - "Hokusai" missed by LLaVA, "Bengal" missed by both

### Hallucinations Observed

| Model | Image | Hallucination |
|-------|-------|---------------|
| MiniCPM-V | Tiger | "row of black spots along tail" (tigers have stripes, not spots) |
| LLaVA | Astronaut | "space shuttle" (image shows free-floating EVA, no shuttle visible) |
| LLaVA | Wave | Sometimes missed Mount Fuji in background |

---

## Production Recommendations

### Use MiniCPM-V 8B For:
- Art identification and analysis
- Scientific/technical image interpretation
- Detailed descriptions requiring context
- Educational content generation
- Any task requiring comprehensive responses

### Use LLaVA 7B For:
- Quick classification tasks
- Time-sensitive applications
- Simple object identification
- When response length doesn't matter

### Neither Model Excels At:
- Wildlife subspecies identification
- Using specific technical terminology
- Street-level urban scene analysis (based on this test)

---

## Gap Analysis: What's Missing

### This Test Did NOT Include:
1. **OCR/Document Images** - Tested separately in Test 1 (MiniCPM-V: 100%, LLaVA: 60%)
2. **Handwriting Recognition** - Covered in Test 1
3. **Charts/Graphs** - Should be added to future tests
4. **Medical/Scientific Diagrams** - Not tested
5. **Screenshots/UI Elements** - Not tested

### Recommendations for Additional Testing:
1. Add receipt/document images to extended set
2. Test with charts and graphs
3. Test with UI screenshots
4. Test with diagrams (flowcharts, architecture diagrams)
5. Test with low-quality/blurry images

---

## Conclusion

The extended benchmark confirms and strengthens the findings from earlier tests:

1. **MiniCPM-V 8B is the superior model for accuracy** (+12% overall)
2. **LLaVA 7B is faster but less comprehensive** (-24% response time, -40% detail)
3. **Both models handle landmarks and common objects well**
4. **MiniCPM-V has significantly better art/cultural knowledge**
5. **Neither model is perfect at technical terminology**

### Final Verdict

For RheaRouter production:
- **Primary Model:** MiniCPM-V 8B (recommended for most use cases)
- **Speed Model:** LLaVA 7B (when latency matters more than detail)

The 12% accuracy advantage of MiniCPM-V is worth the ~1 second additional latency for most applications.

---

*Analysis generated from extended_results.json*
*60 inference requests, 10 images, 3 prompts each, 2 models*
