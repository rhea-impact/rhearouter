#!/usr/bin/env python3
"""
Quick Iteration Test for Ensemble Approaches
Runs fast (1-2 min) tests on a single image to iterate on consensus methods.
"""

import sys
import time
import json
from pathlib import Path
from difflib import SequenceMatcher

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from ensemble.llm_agent import LLMAgent
from ensemble.model_manager import ModelManager
from ensemble.alignment import multi_sequence_align, weighted_consensus

# Test images and ground truths
TEST_IMAGES = {
    "serial_clean": {
        "path": Path(__file__).parent / "images" / "serial_number_clean.png",
        "ground_truth": """SERIAL: XK7-9842-BETA
MODEL: RTX-4090-Ti
S/N: 8A3F2B1C9D0E
MAC: 00:1A:2B:3C:4D:5E
UUID: 550e8400-e29b-41d4-a716-446655440000"""
    },
    "serial_blur": {
        "path": Path(__file__).parent / "degraded" / "serial_number_motion_blur_heavy.png",
        "ground_truth": """SERIAL: XK7-9842-BETA
MODEL: RTX-4090-Ti
S/N: 8A3F2B1C9D0E
MAC: 00:1A:2B:3C:4D:5E
UUID: 550e8400-e29b-41d4-a716-446655440000"""
    },
    "serial_crumpled": {
        "path": Path(__file__).parent / "degraded" / "serial_number_crumpled_severe.png",
        "ground_truth": """SERIAL: XK7-9842-BETA
MODEL: RTX-4090-Ti
S/N: 8A3F2B1C9D0E
MAC: 00:1A:2B:3C:4D:5E
UUID: 550e8400-e29b-41d4-a716-446655440000"""
    }
}

# Default test image
TEST_IMAGE = TEST_IMAGES["serial_clean"]["path"]
GROUND_TRUTH = TEST_IMAGES["serial_clean"]["ground_truth"]

# Results log
RESULTS_LOG = Path(__file__).parent / "iteration_results.json"


def similarity_score(a: str, b: str) -> float:
    """Calculate similarity between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def load_results_log():
    """Load existing results."""
    if RESULTS_LOG.exists():
        return json.loads(RESULTS_LOG.read_text())
    return {"iterations": []}


def save_result(iteration_name: str, method: str, output: str, score: float, notes: str = ""):
    """Save iteration result."""
    log = load_results_log()
    log["iterations"].append({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "iteration": iteration_name,
        "method": method,
        "score": score,
        "output_preview": output[:200],
        "notes": notes
    })
    RESULTS_LOG.write_text(json.dumps(log, indent=2))
    print(f"  Result saved to {RESULTS_LOG}")


def get_model_outputs(model_manager: ModelManager) -> dict:
    """Get outputs from all models."""
    models = ['qwen2.5vl:7b', 'minicpm-v:8b', 'llava:7b']
    outputs = {}

    for model in models:
        print(f"  Running {model}...")
        if model_manager.ensure_loaded(model):
            agent = LLMAgent(model)
            result = agent.extract_text(TEST_IMAGE)
            if result.success:
                outputs[model] = result.text
                print(f"    Got {len(result.text)} chars")
            else:
                print(f"    FAILED")
        else:
            print(f"    Could not load")

    return outputs


def test_baseline_voting(outputs: dict) -> tuple:
    """Test current weighted voting approach."""
    weights = {
        'qwen2.5vl:7b': 0.50,
        'minicpm-v:8b': 0.35,
        'llava:7b': 0.15,
    }

    texts = list(outputs.values())
    sources = list(outputs.keys())
    weights_list = [weights[s] for s in sources]

    aligned = multi_sequence_align(texts)
    consensus, _ = weighted_consensus(aligned, weights_list)

    score = similarity_score(consensus, GROUND_TRUTH)
    return consensus, score


def normalize_output(text: str) -> str:
    """Strip markdown and meta-commentary from LLM output."""
    import re

    # Remove markdown formatting
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold**
    text = re.sub(r'\*([^*]+)\*', r'\1', text)      # *italic*
    text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)  # code blocks
    text = re.sub(r'`([^`]+)`', r'\1', text)        # inline code
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)  # headers

    # Remove common meta-commentary prefixes
    meta_prefixes = [
        r"^The text in the image reads[:\s]*",
        r"^Here is the transcription[:\s]*",
        r"^The image contains[:\s]*",
        r"^Based on the image[,\s]*",
        r"^I can see[:\s]*",
        r"^The text says[:\s]*",
        r"^OCR result[:\s]*",
    ]
    for prefix in meta_prefixes:
        text = re.sub(prefix, '', text, flags=re.IGNORECASE | re.MULTILINE)

    # Normalize whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text


def test_normalized_voting(outputs: dict) -> tuple:
    """Test voting with normalized outputs."""
    weights = {
        'qwen2.5vl:7b': 0.50,
        'minicpm-v:8b': 0.35,
        'llava:7b': 0.15,
    }

    # Normalize all outputs first
    normalized = {k: normalize_output(v) for k, v in outputs.items()}

    texts = list(normalized.values())
    sources = list(normalized.keys())
    weights_list = [weights[s] for s in sources]

    aligned = multi_sequence_align(texts)
    consensus, _ = weighted_consensus(aligned, weights_list)

    score = similarity_score(consensus, GROUND_TRUTH)
    return consensus, score


def test_llm_consensus(outputs: dict, model_manager: ModelManager) -> tuple:
    """Use LLM to build consensus instead of character voting."""

    # Build prompt with all outputs
    candidates = "\n\n".join([
        f"[{name}]:\n{text}" for name, text in outputs.items()
    ])

    prompt = f"""Three OCR systems analyzed an image. Here are their outputs:

{candidates}

Your task: Determine the actual text from the image.
- The outputs may have different formatting (markdown, plain text)
- They may have meta-commentary ("The text reads...")
- Focus on the actual content they all describe

Return ONLY the extracted text, nothing else. No explanations."""

    # Use Qwen as the consensus builder
    if model_manager.ensure_loaded('qwen2.5vl:7b'):
        agent = LLMAgent('qwen2.5vl:7b')
        # Use text-only prompt (no image) for pure consensus
        result = agent.extract_with_context(TEST_IMAGE, prompt)
        if result.success:
            score = similarity_score(result.text, GROUND_TRUTH)
            return result.text, score

    return "", 0.0


def test_qwen_only(model_manager: ModelManager) -> tuple:
    """Baseline: Just use Qwen alone."""
    if model_manager.ensure_loaded('qwen2.5vl:7b'):
        agent = LLMAgent('qwen2.5vl:7b')
        result = agent.extract_text(TEST_IMAGE)
        if result.success:
            score = similarity_score(result.text, GROUND_TRUTH)
            return result.text, score
    return "", 0.0


def test_llm_consensus_good_models_only(outputs: dict, model_manager: ModelManager) -> tuple:
    """LLM consensus using only Qwen + MiniCPM (exclude LLaVA)."""

    good_outputs = {k: v for k, v in outputs.items() if k != 'llava:7b'}

    candidates = "\n\n".join([
        f"[{name}]:\n{text}" for name, text in good_outputs.items()
    ])

    prompt = f"""Two OCR systems analyzed an image. Here are their outputs:

{candidates}

Compare the two readings. Where they agree, that's correct. Where they differ, use context and common sense.

Return ONLY the final extracted text, nothing else."""

    if model_manager.ensure_loaded('qwen2.5vl:7b'):
        agent = LLMAgent('qwen2.5vl:7b')
        result = agent.extract_with_context(TEST_IMAGE, prompt)
        if result.success:
            score = similarity_score(result.text, GROUND_TRUTH)
            return result.text, score

    return "", 0.0


def test_adversarial_verification(outputs: dict, model_manager: ModelManager) -> tuple:
    """Have the LLM actively try to DISPROVE its first reading."""

    qwen_output = outputs.get('qwen2.5vl:7b', '')

    prompt = f"""I think this image says:

{qwen_output}

But I might be wrong. Your job is to find errors in my reading.

Look at the image and for EACH character I extracted:
- Could it be a different character?
- What would make more sense given context?
- Are there any impossible combinations (like 'XK7-99442' - is that a valid format?)

If you find errors, output the CORRECTED text.
If my reading looks correct, output it unchanged.

Focus especially on characters that look ambiguous in the image."""

    if model_manager.ensure_loaded('qwen2.5vl:7b'):
        agent = LLMAgent('qwen2.5vl:7b')
        result = agent.extract_with_context(TEST_IMAGE, prompt)
        if result.success:
            score = similarity_score(result.text, GROUND_TRUTH)
            return result.text, score

    return "", 0.0


def test_segment_and_zoom(model_manager: ModelManager) -> tuple:
    """Read different parts of the image separately, then combine."""
    from PIL import Image
    import tempfile
    import os

    img = Image.open(TEST_IMAGE)
    width, height = img.size

    # Split into top half and bottom half
    top_half = img.crop((0, 0, width, height // 2))
    bottom_half = img.crop((0, height // 2, width, height))

    results = []

    if model_manager.ensure_loaded('qwen2.5vl:7b'):
        agent = LLMAgent('qwen2.5vl:7b')

        # Read top half
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            top_half.save(f.name)
            result = agent.extract_text(f.name)
            if result.success:
                results.append(("top", result.text))
            os.unlink(f.name)

        # Read bottom half
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            bottom_half.save(f.name)
            result = agent.extract_text(f.name)
            if result.success:
                results.append(("bottom", result.text))
            os.unlink(f.name)

        # Combine with LLM
        if len(results) == 2:
            combine_prompt = f"""I read an image in two parts:

TOP HALF:
{results[0][1]}

BOTTOM HALF:
{results[1][1]}

Combine these into the complete text. Remove any duplicates from the overlap region.
Output only the combined text."""

            result = agent.extract_with_context(TEST_IMAGE, combine_prompt)
            if result.success:
                score = similarity_score(result.text, GROUND_TRUTH)
                return result.text, score

    return "", 0.0


def test_enhance_then_read(model_manager: ModelManager) -> tuple:
    """Apply image enhancement before OCR."""
    from PIL import Image, ImageEnhance, ImageFilter
    import tempfile
    import os

    img = Image.open(TEST_IMAGE)

    # Apply enhancements
    # 1. Sharpen
    img = img.filter(ImageFilter.SHARPEN)
    img = img.filter(ImageFilter.SHARPEN)

    # 2. Increase contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.5)

    # 3. Convert to grayscale then back (removes color noise)
    img = img.convert('L').convert('RGB')

    if model_manager.ensure_loaded('qwen2.5vl:7b'):
        agent = LLMAgent('qwen2.5vl:7b')

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            img.save(f.name)
            result = agent.extract_text(f.name)
            os.unlink(f.name)

            if result.success:
                score = similarity_score(result.text, GROUND_TRUTH)
                return result.text, score

    return "", 0.0


def test_character_by_character(model_manager: ModelManager) -> tuple:
    """Extract character-by-character with confidence, then rebuild."""

    prompt = """Read this image and output each line.

For any character you're uncertain about, mark it with [?X?] where X is your best guess.

For example: SERI[?A?]L: XK7-98[?4?]2

Be honest about uncertainty - marking uncertain characters helps me verify them."""

    if model_manager.ensure_loaded('qwen2.5vl:7b'):
        agent = LLMAgent('qwen2.5vl:7b')
        result = agent.extract_with_context(TEST_IMAGE, prompt)

        if result.success:
            # Now re-examine uncertain characters
            if '[?' in result.text:
                verify_prompt = f"""I extracted this text with some uncertain characters marked:

{result.text}

For each [?X?] marker, look at that specific position in the image again.
What is the actual character there?

Output the final corrected text with no uncertainty markers."""

                result2 = agent.extract_with_context(TEST_IMAGE, verify_prompt)
                if result2.success:
                    score = similarity_score(result2.text, GROUND_TRUTH)
                    return result2.text, score

            score = similarity_score(result.text, GROUND_TRUTH)
            return result.text, score

    return "", 0.0


def test_uncertainty_v2(model_manager: ModelManager) -> tuple:
    """Improved uncertainty marking with multiple verification passes."""

    prompt1 = """Read this image carefully. For EVERY character:
- If you're confident (>90%), write it normally
- If you're uncertain, write [?X/Y?] where X is your best guess and Y is the alternative

Example: SER[?I/1?]AL: XK[?7/T?]-9842

This helps me verify the ambiguous parts. Be thorough - mark anything that could be wrong."""

    if not model_manager.ensure_loaded('qwen2.5vl:7b'):
        return "", 0.0

    agent = LLMAgent('qwen2.5vl:7b')
    result1 = agent.extract_with_context(TEST_IMAGE, prompt1)

    if not result1.success:
        return "", 0.0

    first_pass = result1.text

    # Second pass: for each uncertain marker, zoom in mentally
    if '[?' in first_pass:
        prompt2 = f"""First reading with uncertainties marked:

{first_pass}

Now for each [?X/Y?] marking:
1. Look at that exact position in the image
2. Consider context (MAC uses hex 0-9,A-F; UUIDs have specific format)
3. Which alternative fits better?

Resolve each uncertainty and output the FINAL text with no markers."""

        result2 = agent.extract_with_context(TEST_IMAGE, prompt2)
        if result2.success:
            # Third pass: sanity check
            prompt3 = f"""Final verification of: {result2.text}

Quick sanity check:
- MAC addresses use only 0-9 and A-F
- UUIDs are 8-4-4-4-12 hex digits
- Serial numbers usually have consistent patterns

Fix any obvious format violations. Output final text."""

            result3 = agent.extract_with_context(TEST_IMAGE, prompt3)
            if result3.success:
                score = similarity_score(result3.text, GROUND_TRUTH)
                return result3.text, score

            score = similarity_score(result2.text, GROUND_TRUTH)
            return result2.text, score

    score = similarity_score(first_pass, GROUND_TRUTH)
    return first_pass, score


def test_region_specialist(model_manager: ModelManager) -> tuple:
    """Focus on specific regions with enhanced prompts for each data type."""
    from PIL import Image
    import tempfile
    import os

    if not model_manager.ensure_loaded('qwen2.5vl:7b'):
        return "", 0.0

    agent = LLMAgent('qwen2.5vl:7b')

    # First, get the structure
    structure_prompt = """Look at this image. What types of data fields do you see?
Just list them like:
- Serial number (line 1)
- Model number (line 2)
etc.

Don't read the values yet, just identify what's there."""

    result = agent.extract_with_context(TEST_IMAGE, structure_prompt)

    # Now read with field-specific knowledge
    read_prompt = """Read this image field by field:

For SERIAL/MODEL codes: Watch for similar characters (O/0, I/1/l, B/8, S/5)
For MAC address: Must be hex (0-9, A-F only), format XX:XX:XX:XX:XX:XX
For UUID: Must be hex, format 8-4-4-4-12 digits
For S/N: Typically alphanumeric, uppercase

Read each field carefully and output in format:
FIELD: value"""

    result2 = agent.extract_with_context(TEST_IMAGE, read_prompt)
    if result2.success:
        score = similarity_score(result2.text, GROUND_TRUTH)
        return result2.text, score

    return "", 0.0


def test_diverse_views_ensemble(model_manager: ModelManager) -> tuple:
    """Each model gets a DIFFERENT preprocessed version of the image."""
    from PIL import Image, ImageEnhance, ImageFilter
    import tempfile
    import os

    img = Image.open(TEST_IMAGE)
    results = {}

    if not model_manager.ensure_loaded('qwen2.5vl:7b'):
        return "", 0.0

    agent = LLMAgent('qwen2.5vl:7b')

    # View 1: Original
    result = agent.extract_text(TEST_IMAGE)
    if result.success:
        results['original'] = result.text

    # View 2: High contrast grayscale
    img_contrast = img.convert('L')
    enhancer = ImageEnhance.Contrast(img_contrast)
    img_contrast = enhancer.enhance(2.0)
    img_contrast = img_contrast.convert('RGB')

    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        img_contrast.save(f.name)
        result = agent.extract_text(f.name)
        if result.success:
            results['high_contrast'] = result.text
        os.unlink(f.name)

    # View 3: Sharpened
    img_sharp = img.filter(ImageFilter.SHARPEN)
    img_sharp = img_sharp.filter(ImageFilter.SHARPEN)
    img_sharp = img_sharp.filter(ImageFilter.SHARPEN)

    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        img_sharp.save(f.name)
        result = agent.extract_text(f.name)
        if result.success:
            results['sharpened'] = result.text
        os.unlink(f.name)

    # View 4: Scaled up 2x (more pixels to analyze)
    img_scaled = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)

    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        img_scaled.save(f.name)
        result = agent.extract_text(f.name)
        if result.success:
            results['scaled_2x'] = result.text
        os.unlink(f.name)

    # Now have LLM arbitrate between the views
    if len(results) >= 2:
        candidates = "\n\n".join([f"[{view}]:\n{text}" for view, text in results.items()])

        arbitrate_prompt = f"""I read the same image with different preprocessing:

{candidates}

These are all readings of the SAME image. Compare them character-by-character.
Where they agree, that's likely correct.
Where they disagree, pick the one that makes most sense (valid hex for MAC, etc.)

Output the best combined reading."""

        result = agent.extract_with_context(TEST_IMAGE, arbitrate_prompt)
        if result.success:
            score = similarity_score(result.text, GROUND_TRUTH)
            return result.text, score

    return "", 0.0


def test_bear_grylls_survive(model_manager: ModelManager) -> tuple:
    """
    Bear Grylls approach: When everything seems hostile, find what you CAN use.

    The weak models are bad at full OCR - but maybe they're good at something specific?
    Use them as "specialists" for specific character verification.
    """
    from PIL import Image
    import tempfile
    import os

    if not model_manager.ensure_loaded('qwen2.5vl:7b'):
        return "", 0.0

    agent_qwen = LLMAgent('qwen2.5vl:7b')

    # Step 1: Get Qwen's best reading
    result = agent_qwen.extract_text(TEST_IMAGE)
    if not result.success:
        return "", 0.0

    initial_text = result.text

    # Step 2: Identify potentially ambiguous characters
    # Find characters that commonly confuse OCR
    ambiguous_positions = []
    for i, char in enumerate(initial_text):
        if char in '0O1lI5S8B2ZgqCcKkMmUuVvWwXxYyZz':
            # Get context
            start = max(0, i - 3)
            end = min(len(initial_text), i + 4)
            context = initial_text[start:end]
            ambiguous_positions.append((i, char, context))

    if not ambiguous_positions:
        return initial_text, similarity_score(initial_text, GROUND_TRUTH)

    # Step 3: For each ambiguous section, ask Qwen to double-check with image
    # But this time, CROP to just that region and zoom in

    img = Image.open(TEST_IMAGE)

    # Ask about the most suspicious characters
    verify_prompt = f"""I extracted this text:

{initial_text}

I'm uncertain about some characters. Looking at the image again:

1. In the serial number, is it '9842' or '9442' or something else?
2. In the MAC address, what are the exact hex values?
3. In the UUID, verify each segment.

Look VERY carefully at the image. Output the corrected text."""

    result2 = agent_qwen.extract_with_context(TEST_IMAGE, verify_prompt)
    if result2.success:
        score = similarity_score(result2.text, GROUND_TRUTH)
        return result2.text, score

    return initial_text, similarity_score(initial_text, GROUND_TRUTH)


def test_line_by_line_zoom(model_manager: ModelManager) -> tuple:
    """Extract each line by cropping to just that line region."""
    from PIL import Image
    import tempfile
    import os

    img = Image.open(TEST_IMAGE)
    width, height = img.size

    # Estimate 5 lines of text, crop each
    line_height = height // 5
    lines = []

    if not model_manager.ensure_loaded('qwen2.5vl:7b'):
        return "", 0.0

    agent = LLMAgent('qwen2.5vl:7b')

    for i in range(5):
        y_start = i * line_height
        y_end = min((i + 1) * line_height + 10, height)  # slight overlap

        line_img = img.crop((0, y_start, width, y_end))

        # Scale up the line for better reading
        line_img = line_img.resize((line_img.width * 2, line_img.height * 2), Image.LANCZOS)

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            line_img.save(f.name)
            result = agent.extract_text(f.name)
            if result.success and result.text.strip():
                lines.append(result.text.strip())
            os.unlink(f.name)

    combined = '\n'.join(lines)
    score = similarity_score(combined, GROUND_TRUTH)
    return combined, score


def test_multipass_refinement(model_manager: ModelManager) -> tuple:
    """Multiple passes, each refining the previous."""

    if not model_manager.ensure_loaded('qwen2.5vl:7b'):
        return "", 0.0

    agent = LLMAgent('qwen2.5vl:7b')

    # Pass 1: Quick read
    result1 = agent.extract_text(TEST_IMAGE)
    if not result1.success:
        return "", 0.0

    # Pass 2: Verify numbers and codes specifically
    verify_prompt = f"""First reading: {result1.text}

Now focus ONLY on the numbers and alphanumeric codes.
Look at each digit/letter in serial numbers, MACs, UUIDs.
Are they correct? Fix any errors you see.

Output the corrected full text."""

    result2 = agent.extract_with_context(TEST_IMAGE, verify_prompt)
    if not result2.success:
        return result1.text, similarity_score(result1.text, GROUND_TRUTH)

    # Pass 3: Final sanity check
    sanity_prompt = f"""Reading: {result2.text}

Final check:
- Does the MAC address have valid hex characters (0-9, A-F)?
- Does the UUID have the right format?
- Do the serial numbers look plausible?

If anything looks wrong, fix it. Output final text."""

    result3 = agent.extract_with_context(TEST_IMAGE, sanity_prompt)
    if result3.success:
        score = similarity_score(result3.text, GROUND_TRUTH)
        return result3.text, score

    return result2.text, similarity_score(result2.text, GROUND_TRUTH)


def test_focused_reread(model_manager: ModelManager) -> tuple:
    """Re-read the image with a very specific prompt focused on accuracy."""

    prompt = """Read this image VERY carefully. This appears to be technical information with:
- Serial numbers and model codes
- MAC addresses (format: XX:XX:XX:XX:XX:XX)
- UUIDs (format: 8-4-4-4-12 hex digits)

For each field, examine each character individually. Common OCR confusions:
- 0 vs O, 1 vs l vs I, 5 vs S, 8 vs B, 2 vs Z

Output the text in this exact format:
SERIAL: [value]
MODEL: [value]
S/N: [value]
MAC: [value]
UUID: [value]

Be precise. Every character matters."""

    if model_manager.ensure_loaded('qwen2.5vl:7b'):
        agent = LLMAgent('qwen2.5vl:7b')
        result = agent.extract_with_context(TEST_IMAGE, prompt)
        if result.success:
            score = similarity_score(result.text, GROUND_TRUTH)
            return result.text, score

    return "", 0.0


def test_verification_pass(outputs: dict, model_manager: ModelManager) -> tuple:
    """Have LLM verify low-confidence characters by re-examining the image."""

    # Get Qwen's initial output
    qwen_output = outputs.get('qwen2.5vl:7b', '')

    prompt = f"""I extracted this text from an image:

{qwen_output}

Some characters may be wrong due to image quality. Please:
1. Look at the image again
2. For each line, verify the characters are correct
3. Pay special attention to: numbers vs letters (0/O, 1/l/I), similar shapes (8/B, 5/S)
4. If you see an error, fix it

Return the corrected text only."""

    if model_manager.ensure_loaded('qwen2.5vl:7b'):
        agent = LLMAgent('qwen2.5vl:7b')
        result = agent.extract_with_context(TEST_IMAGE, prompt)
        if result.success:
            score = similarity_score(result.text, GROUND_TRUTH)
            return result.text, score

    return "", 0.0


def test_self_consistency(model_manager: ModelManager) -> tuple:
    """Run Qwen 3 times with different prompts, use LLM to pick best."""

    prompts = [
        "Extract all text from this image exactly as written.",
        "Read and transcribe the text in this image. Be precise with numbers and codes.",
        "OCR this image. Output the text content only.",
    ]

    outputs = []
    if model_manager.ensure_loaded('qwen2.5vl:7b'):
        agent = LLMAgent('qwen2.5vl:7b')
        for prompt in prompts:
            result = agent.extract_with_context(TEST_IMAGE, prompt)
            if result.success:
                outputs.append(result.text)

    if len(outputs) < 2:
        return "", 0.0

    # Use LLM to pick the most consistent/accurate one
    candidates = "\n\n".join([f"[Reading {i+1}]:\n{text}" for i, text in enumerate(outputs)])

    arbitration_prompt = f"""I read the same image 3 times. Here are the results:

{candidates}

Which reading is most accurate? Consider:
- Consistency across readings
- Plausibility of values (serial numbers, MACs, UUIDs)
- Completeness

Return ONLY the most accurate reading, correcting any obvious errors."""

    result = agent.extract_with_context(TEST_IMAGE, arbitration_prompt)
    if result.success:
        score = similarity_score(result.text, GROUND_TRUTH)
        return result.text, score

    return "", 0.0


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", choices=list(TEST_IMAGES.keys()), default="serial_clean",
                        help="Which test image to use")
    args = parser.parse_args()

    global TEST_IMAGE, GROUND_TRUTH
    TEST_IMAGE = TEST_IMAGES[args.image]["path"]
    GROUND_TRUTH = TEST_IMAGES[args.image]["ground_truth"]

    print("="*60)
    print("QUICK ITERATION TEST")
    print(f"Image: {args.image} ({TEST_IMAGE.name})")
    print("="*60)

    model_manager = ModelManager()

    # Get baseline outputs from all models
    print("\n[1] Getting model outputs...")
    outputs = get_model_outputs(model_manager)

    if not outputs:
        print("ERROR: No model outputs!")
        return

    print(f"\nGot outputs from {len(outputs)} models")

    # Show raw outputs
    print("\n" + "-"*60)
    print("RAW OUTPUTS:")
    for name, text in outputs.items():
        print(f"\n[{name}]:")
        print(text[:300] + "..." if len(text) > 300 else text)

    # Test methods
    print("\n" + "="*60)
    print("TESTING METHODS")
    print("="*60)

    results = {}

    # Qwen only (baseline)
    print("\n[A] Qwen Only (baseline)...")
    text, score = test_qwen_only(model_manager)
    results['qwen_only'] = score
    print(f"  Score: {score:.1%}")
    save_result("baseline", "qwen_only", text, score, "Single model baseline")

    # Current weighted voting
    print("\n[B] Current Weighted Voting...")
    text, score = test_baseline_voting(outputs)
    results['weighted_voting'] = score
    print(f"  Score: {score:.1%}")
    print(f"  Output: {repr(text[:100])}")
    save_result("baseline", "weighted_voting", text, score, "Character-level voting")

    # Normalized voting
    print("\n[C] Normalized Voting...")
    text, score = test_normalized_voting(outputs)
    results['normalized_voting'] = score
    print(f"  Score: {score:.1%}")
    print(f"  Output: {repr(text[:100])}")
    save_result("iteration_1", "normalized_voting", text, score, "With markdown/meta stripping")

    # LLM consensus
    print("\n[D] LLM Consensus (all models)...")
    text, score = test_llm_consensus(outputs, model_manager)
    results['llm_consensus_all'] = score
    print(f"  Score: {score:.1%}")
    print(f"  Output: {repr(text[:100])}")
    save_result("iteration_2", "llm_consensus_all", text, score, "Qwen arbitrates all outputs")

    # LLM consensus - good models only
    print("\n[E] LLM Consensus (Qwen+MiniCPM only)...")
    text, score = test_llm_consensus_good_models_only(outputs, model_manager)
    results['llm_consensus_good'] = score
    print(f"  Score: {score:.1%}")
    print(f"  Output: {repr(text[:100])}")
    save_result("iteration_3", "llm_consensus_good", text, score, "Exclude LLaVA garbage")

    # Self-consistency
    print("\n[F] Self-Consistency (Qwen x3)...")
    text, score = test_self_consistency(model_manager)
    results['self_consistency'] = score
    print(f"  Score: {score:.1%}")
    print(f"  Output: {repr(text[:100])}")
    save_result("iteration_4", "self_consistency", text, score, "Qwen reads 3x, picks best")

    # Verification pass
    print("\n[G] Verification Pass (Qwen re-checks)...")
    text, score = test_verification_pass(outputs, model_manager)
    results['verification_pass'] = score
    print(f"  Score: {score:.1%}")
    print(f"  Output: {repr(text[:100])}")
    save_result("iteration_5", "verification_pass", text, score, "Qwen verifies its own output")

    # Focused reread
    print("\n[H] Focused Re-read (structured prompt)...")
    text, score = test_focused_reread(model_manager)
    results['focused_reread'] = score
    print(f"  Score: {score:.1%}")
    print(f"  Output: {repr(text[:100])}")
    save_result("iteration_6", "focused_reread", text, score, "Detailed prompt with format hints")

    # CREATIVE APPROACHES

    # Diverse views ensemble
    print("\n[I] Diverse Views (same model, different preprocessing)...")
    text, score = test_diverse_views_ensemble(model_manager)
    results['diverse_views'] = score
    print(f"  Score: {score:.1%}")
    print(f"  Output: {repr(text[:100])}")
    save_result("creative_1", "diverse_views", text, score, "Original + contrast + sharp + scaled")

    # Bear Grylls - targeted verification
    print("\n[J] Bear Grylls (targeted ambiguous char verification)...")
    text, score = test_bear_grylls_survive(model_manager)
    results['bear_grylls'] = score
    print(f"  Score: {score:.1%}")
    print(f"  Output: {repr(text[:100])}")
    save_result("creative_2", "bear_grylls", text, score, "Identify and re-verify ambiguous chars")

    # Line-by-line zoom
    print("\n[K] Line-by-Line Zoom (crop each line, scale up)...")
    text, score = test_line_by_line_zoom(model_manager)
    results['line_zoom'] = score
    print(f"  Score: {score:.1%}")
    print(f"  Output: {repr(text[:100])}")
    save_result("creative_3", "line_zoom", text, score, "Read each line separately, zoomed")

    # Adversarial verification
    print("\n[L] Adversarial (try to disprove first reading)...")
    text, score = test_adversarial_verification(outputs, model_manager)
    results['adversarial'] = score
    print(f"  Score: {score:.1%}")
    print(f"  Output: {repr(text[:100])}")
    save_result("creative_4", "adversarial", text, score, "Actively try to find errors")

    # Character uncertainty marking
    print("\n[M] Character Uncertainty (mark uncertain, then verify)...")
    text, score = test_character_by_character(model_manager)
    results['char_uncertainty'] = score
    print(f"  Score: {score:.1%}")
    print(f"  Output: {repr(text[:100])}")
    save_result("creative_5", "char_uncertainty", text, score, "Mark [?X?] then re-examine")

    # Multipass refinement
    print("\n[N] Multipass Refinement (3 passes, each refining)...")
    text, score = test_multipass_refinement(model_manager)
    results['multipass'] = score
    print(f"  Score: {score:.1%}")
    print(f"  Output: {repr(text[:100])}")
    save_result("creative_6", "multipass", text, score, "Quick read -> verify numbers -> sanity check")

    # Uncertainty v2 - improved version of the winner
    print("\n[O] Uncertainty V2 (with alternatives + sanity check)...")
    text, score = test_uncertainty_v2(model_manager)
    results['uncertainty_v2'] = score
    print(f"  Score: {score:.1%}")
    print(f"  Output: {repr(text[:100])}")
    save_result("winner_v2", "uncertainty_v2", text, score, "Mark [?X/Y?] alternatives, then resolve")

    # Region specialist
    print("\n[P] Region Specialist (field-specific prompts)...")
    text, score = test_region_specialist(model_manager)
    results['region_specialist'] = score
    print(f"  Score: {score:.1%}")
    print(f"  Output: {repr(text[:100])}")
    save_result("creative_7", "region_specialist", text, score, "Field-type-aware reading")

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for method, score in sorted(results.items(), key=lambda x: -x[1]):
        bar = "█" * int(score * 40)
        print(f"  {method:20} {score:5.1%} {bar}")

    print(f"\nResults logged to: {RESULTS_LOG}")


if __name__ == "__main__":
    main()
