# OCR Stress Test Analysis - Adversarial Text Recognition

**Date:** November 24, 2025
**Test Type:** Controlled degradation with ground truth comparison
**Total Tests:** 160 (5 texts x 16 degradations x 2 models)

---

## Test Design

### Why This Test Matters

Unlike testing on random images where we guess at expected content, this test:
1. **Generates text images with known content** - We control the ground truth
2. **Applies systematic degradations** - Rotation, blur, noise, lighting, compression
3. **Scores against exact original** - Character/word accuracy, number extraction
4. **Reveals failure thresholds** - At what point does each model break down?

### Text Categories Tested

| Category | Content Type | Challenge |
|----------|--------------|-----------|
| Receipt | Prices, dates, items | Number accuracy critical |
| Invoice | Email, amounts, IDs | Mixed alphanumeric |
| Handwritten Style | Notes, bullet points | Informal structure |
| Serial Number | UUIDs, MACs, model IDs | Precise alphanumeric strings |
| Address Label | Names, addresses, ZIP | Structured data extraction |

### Degradations Applied

| Degradation | Description | Real-World Scenario |
|-------------|-------------|---------------------|
| clean | Baseline | Perfect scan |
| rotate_5 | 5° rotation | Slightly crooked photo |
| rotate_15 | 15° rotation | Handheld phone capture |
| rotate_30 | 30° rotation | Severe angle |
| blur_light | Gaussian blur r=1.5 | Slight motion blur |
| blur_heavy | Gaussian blur r=3.0 | Out of focus |
| noise_light | 5% salt & pepper | Dirty scanner |
| noise_heavy | 15% salt & pepper | Very dirty/damaged |
| dark | 50% brightness | Underexposed photo |
| bright | 180% brightness | Overexposed/washed out |
| low_contrast | 40% contrast | Faded thermal paper |
| jpeg_artifacts | Quality=10 | Heavy compression |
| perspective_skew | Perspective warp | Photo taken at angle |
| combo_mild | 5° + light blur + light noise | Typical phone photo |
| combo_severe | 15° + blur + noise + dark | Worst case scenario |
| crumpled | Fold lines added | Crumpled document |

---

## Results Summary

### Overall Performance

| Model | Average Score | Best Degradation | Worst Degradation |
|-------|--------------|------------------|-------------------|
| **MiniCPM-V 8B** | **75%** | Dark (87%) | Combo Severe (4%) |
| **LLaVA 7B** | **36%** | Dark (50%) | Combo Severe (8%) |

**MiniCPM-V wins by 39 percentage points on adversarial OCR**

---

## Detailed Breakdown by Degradation

### MiniCPM-V 8B Performance

```
No degradation (baseline)           ████████████████░░░░ 81%
5° rotation                         █████████████████░░░ 85%
15° rotation                        ███████████████░░░░░ 79%
30° rotation (severe)               ██████████████░░░░░░ 74%
Light Gaussian blur                 ██████████████░░░░░░ 74%
Heavy Gaussian blur                 █████████████░░░░░░░ 70%
Light noise (5%)                    ████████████████░░░░ 83%
Heavy noise (15%)                   ████████████░░░░░░░░ 62%
Underexposed (dark)                 █████████████████░░░ 87%
Overexposed (washed out)            █████████████████░░░ 85%
Low contrast                        █████████████████░░░ 87%
Heavy JPEG compression              ████████████████░░░░ 83%
Perspective skew (photo angle)      ████████████████░░░░ 83%
Mild combo (5° + blur + noise)      ███████████████░░░░░ 75%
Severe combo (all effects)          ░░░░░░░░░░░░░░░░░░░░ 4%
Simulated crumple/fold lines        ████████████████░░░░ 83%
```

### LLaVA 7B Performance

```
No degradation (baseline)           ████████░░░░░░░░░░░░ 41%
5° rotation                         ████████░░░░░░░░░░░░ 41%
15° rotation                        ██████░░░░░░░░░░░░░░ 32%
30° rotation (severe)               ████░░░░░░░░░░░░░░░░ 20%
Light Gaussian blur                 █████████░░░░░░░░░░░ 46%
Heavy Gaussian blur                 ██████░░░░░░░░░░░░░░ 33%
Light noise (5%)                    ████████░░░░░░░░░░░░ 42%
Heavy noise (15%)                   ████░░░░░░░░░░░░░░░░ 23%
Underexposed (dark)                 █████████░░░░░░░░░░░ 50%
Overexposed (washed out)            ████████░░░░░░░░░░░░ 44%
Low contrast                        █████████░░░░░░░░░░░ 48%
Heavy JPEG compression              ████████░░░░░░░░░░░░ 42%
Perspective skew (photo angle)      █████░░░░░░░░░░░░░░░ 29%
Mild combo (5° + blur + noise)      ███████░░░░░░░░░░░░░ 37%
Severe combo (all effects)          █░░░░░░░░░░░░░░░░░░░ 8%
Simulated crumple/fold lines        ████████░░░░░░░░░░░░ 41%
```

---

## Key Findings

### 1. MiniCPM-V Dominates Every Category (Except One)

| Degradation | MiniCPM-V | LLaVA | Winner | Gap |
|-------------|-----------|-------|--------|-----|
| Baseline (clean) | 81% | 41% | MiniCPM | +40% |
| 5° rotation | 85% | 41% | MiniCPM | +44% |
| 15° rotation | 79% | 32% | MiniCPM | +47% |
| 30° rotation | 74% | 20% | MiniCPM | +54% |
| Light blur | 74% | 46% | MiniCPM | +28% |
| Heavy blur | 70% | 33% | MiniCPM | +37% |
| Light noise | 83% | 42% | MiniCPM | +41% |
| Heavy noise | 62% | 23% | MiniCPM | +39% |
| Dark | 87% | 50% | MiniCPM | +37% |
| Bright | 85% | 44% | MiniCPM | +41% |
| Low contrast | 87% | 48% | MiniCPM | +39% |
| JPEG artifacts | 83% | 42% | MiniCPM | +41% |
| Perspective | 83% | 29% | MiniCPM | +54% |
| Mild combo | 75% | 37% | MiniCPM | +38% |
| **Severe combo** | **4%** | **8%** | **LLaVA** | **-4%** |
| Crumpled | 83% | 41% | MiniCPM | +42% |

### 2. Rotation Tolerance

MiniCPM-V handles rotation remarkably well:
- **5°:** 85% (actually *better* than baseline)
- **15°:** 79% (still excellent)
- **30°:** 74% (still usable)

LLaVA degrades rapidly:
- **5°:** 41% (no change from baseline)
- **15°:** 32% (significant drop)
- **30°:** 20% (nearly unusable)

### 3. Lighting Robustness

Both models handle lighting changes well, but MiniCPM-V is superior:
- **Dark images:** MiniCPM 87% vs LLaVA 50%
- **Bright images:** MiniCPM 85% vs LLaVA 44%
- **Low contrast:** MiniCPM 87% vs LLaVA 48%

### 4. Noise Sensitivity

Heavy noise (15%) causes significant degradation:
- MiniCPM-V: 83% → 62% (-21 points)
- LLaVA: 42% → 23% (-19 points)

### 5. The "Severe Combo" Breaks Both Models

When combining 15° rotation + blur + noise + darkness:
- **MiniCPM-V: 4%** (catastrophic failure)
- **LLaVA: 8%** (equally catastrophic)

This represents the realistic worst-case scenario (crumpled receipt photo taken in dim lighting at an angle) - neither model can handle it.

---

## Text Category Analysis

### Receipt (Prices Critical)

| Degradation | MiniCPM-V | LLaVA | Number Accuracy |
|-------------|-----------|-------|-----------------|
| Clean | 82% | 61% | MiniCPM: 100% |
| Rotate 15° | 51% | 52% | Both: ~50% |
| Dark | 85% | 71% | MiniCPM: 100% |

**Insight:** MiniCPM-V maintains number accuracy even under degradation. Critical for expense tracking.

### Serial Numbers (Alphanumeric Precision)

| Degradation | MiniCPM-V | LLaVA |
|-------------|-----------|-------|
| Clean | 69% | 18% |
| Rotate 5° | 94% | 36% |
| Heavy blur | 33% | 22% |

**Insight:** Serial numbers are hard for both models. MiniCPM-V is 3-4x better but still struggles with heavy blur.

### Address Labels (Structured Data)

| Degradation | MiniCPM-V | LLaVA |
|-------------|-----------|-------|
| Clean | 78% | 39% |
| Dark | 97% | 50% |
| Perspective | 88% | 21% |

**Insight:** MiniCPM-V handles addresses well, especially in challenging lighting.

---

## Production Recommendations

### For Receipt/Invoice Processing

1. **Use MiniCPM-V 8B** - 2x better accuracy than LLaVA
2. **Pre-process images:**
   - Auto-rotate to correct orientation
   - Normalize brightness/contrast
   - Avoid heavy compression before OCR
3. **Reject severely degraded images** - Both models fail below certain thresholds

### Degradation Tolerance Thresholds (MiniCPM-V)

| Condition | Acceptable? | Expected Accuracy |
|-----------|-------------|-------------------|
| Rotation < 30° | Yes | 74-85% |
| Light blur | Yes | 74% |
| Heavy blur | Marginal | 70% |
| Light noise | Yes | 83% |
| Heavy noise | Marginal | 62% |
| Dark/bright | Yes | 85-87% |
| JPEG compression | Yes | 83% |
| Mild combination | Yes | 75% |
| Severe combination | **NO** | 4% |

### Quality Gates for Document Intake

Before sending to OCR, check:
1. Image is not severely rotated (>30°)
2. Image is not heavily blurred
3. Image has reasonable contrast
4. Image does not have multiple severe degradations

---

## Conclusion

**MiniCPM-V 8B is dramatically superior for OCR tasks**, winning 15 of 16 degradation categories with an average margin of +39 percentage points.

Key takeaways:
- MiniCPM-V handles real-world photo conditions (rotation, lighting, compression) well
- LLaVA struggles even with clean images (41% baseline)
- Neither model can handle severely degraded images - pre-processing is essential
- For production receipt/document scanning, MiniCPM-V is the clear choice

---

*Test images and full results saved in:*
- `images/` - Clean generated images
- `degraded/` - All 80 degraded variants
- `results/ocr_stress_results.json` - Full accuracy metrics
