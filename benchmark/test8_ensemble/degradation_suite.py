"""
Extreme Degradation Suite for RheaRouter Ensemble Testing

Designed to push vision models to their limits, creating adversarial
conditions that drop Qwen2.5-VL from 95% to 85% accuracy.

The goal: Demonstrate that ensemble techniques recover lost accuracy.
"""

import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
from io import BytesIO
from typing import Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class DegradationConfig:
    """Configuration for a degradation type."""
    name: str
    description: str
    severity: str  # "mild", "moderate", "severe", "extreme"
    params: Dict


# =============================================================================
# TIER 1: Enhanced Single Effects
# =============================================================================

def apply_motion_blur(img: Image.Image, length: int = 15, angle: int = 0) -> Image.Image:
    """Apply directional motion blur (simulates camera shake)."""
    # Create motion blur kernel
    kernel_size = length
    kernel = np.zeros((kernel_size, kernel_size))

    # Draw a line at the specified angle
    center = kernel_size // 2
    rad = np.deg2rad(angle)

    for i in range(kernel_size):
        offset = i - center
        x = int(center + offset * np.cos(rad))
        y = int(center + offset * np.sin(rad))
        if 0 <= x < kernel_size and 0 <= y < kernel_size:
            kernel[y, x] = 1

    kernel = kernel / kernel.sum()

    # Apply using convolution
    from PIL import ImageFilter

    arr = np.array(img)
    from scipy import ndimage
    result = np.zeros_like(arr)

    for c in range(3):
        result[:, :, c] = ndimage.convolve(arr[:, :, c], kernel)

    return Image.fromarray(result.astype(np.uint8))


def apply_defocus_blur(img: Image.Image, radius: int = 5) -> Image.Image:
    """Apply disk-shaped defocus blur (out-of-focus lens)."""
    # Create circular kernel
    y, x = np.ogrid[-radius:radius + 1, -radius:radius + 1]
    mask = x ** 2 + y ** 2 <= radius ** 2
    kernel = mask.astype(float)
    kernel = kernel / kernel.sum()

    arr = np.array(img)
    from scipy import ndimage
    result = np.zeros_like(arr)

    for c in range(3):
        result[:, :, c] = ndimage.convolve(arr[:, :, c], kernel)

    return Image.fromarray(result.astype(np.uint8))


def apply_film_grain(img: Image.Image, intensity: float = 0.2) -> Image.Image:
    """Add realistic film grain noise."""
    arr = np.array(img).astype(float)

    # Generate grain pattern
    grain = np.random.normal(0, intensity * 50, arr.shape)

    # Apply grain
    result = arr + grain
    result = np.clip(result, 0, 255)

    return Image.fromarray(result.astype(np.uint8))


def apply_speckle_noise(img: Image.Image, intensity: float = 0.15) -> Image.Image:
    """Add multiplicative speckle noise (radar-like)."""
    arr = np.array(img).astype(float)

    # Speckle noise is multiplicative
    speckle = np.random.normal(1, intensity, arr.shape)
    result = arr * speckle
    result = np.clip(result, 0, 255)

    return Image.fromarray(result.astype(np.uint8))


def apply_uneven_lighting(img: Image.Image, pattern: str = "gradient_lr") -> Image.Image:
    """Apply uneven lighting patterns."""
    arr = np.array(img).astype(float)
    h, w = arr.shape[:2]

    if pattern == "gradient_lr":
        # Left to right gradient
        gradient = np.linspace(0.5, 1.5, w)
        gradient = np.tile(gradient, (h, 1))
    elif pattern == "gradient_tb":
        # Top to bottom gradient
        gradient = np.linspace(1.5, 0.5, h)
        gradient = np.tile(gradient.reshape(-1, 1), (1, w))
    elif pattern == "spotlight":
        # Central spotlight
        y, x = np.ogrid[:h, :w]
        center_y, center_x = h // 2, w // 2
        dist = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
        max_dist = np.sqrt(center_x ** 2 + center_y ** 2)
        gradient = 1.5 - (dist / max_dist)
    elif pattern == "shadow_band":
        # Horizontal shadow band
        gradient = np.ones((h, w))
        band_start = h // 3
        band_end = 2 * h // 3
        gradient[band_start:band_end, :] = 0.5
    else:
        gradient = np.ones((h, w))

    gradient = gradient.reshape(h, w, 1)
    result = arr * gradient
    result = np.clip(result, 0, 255)

    return Image.fromarray(result.astype(np.uint8))


def apply_vignette(img: Image.Image, strength: float = 0.5) -> Image.Image:
    """Apply vignette (edge darkening)."""
    arr = np.array(img).astype(float)
    h, w = arr.shape[:2]

    # Create vignette mask
    y, x = np.ogrid[:h, :w]
    center_y, center_x = h // 2, w // 2

    # Normalized distance from center
    max_dist = np.sqrt(center_x ** 2 + center_y ** 2)
    dist = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
    norm_dist = dist / max_dist

    # Vignette factor
    vignette = 1 - (norm_dist ** 2) * strength
    vignette = vignette.reshape(h, w, 1)

    result = arr * vignette
    result = np.clip(result, 0, 255)

    return Image.fromarray(result.astype(np.uint8))


# =============================================================================
# TIER 2: Real-World Damage Scenarios
# =============================================================================

def apply_water_damage(img: Image.Image, intensity: float = 0.4) -> Image.Image:
    """Simulate water damage with stains and ink bleed."""
    arr = np.array(img).astype(float)
    h, w = arr.shape[:2]

    # Add water ring stains
    num_stains = random.randint(1, 3)
    for _ in range(num_stains):
        cx, cy = random.randint(0, w), random.randint(0, h)
        radius = random.randint(30, 80)

        y, x = np.ogrid[:h, :w]
        dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)

        # Ring pattern
        ring = (np.abs(dist - radius) < 10).astype(float) * intensity * 0.3
        ring = ring.reshape(h, w, 1)

        # Brown tint for coffee stain
        stain_color = np.array([0.8, 0.6, 0.4])
        arr = arr * (1 - ring) + arr * ring * stain_color

    # Add slight blur for ink bleed effect
    result = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    result = result.filter(ImageFilter.GaussianBlur(radius=0.8))

    return result


def apply_thermal_fade(img: Image.Image, intensity: float = 0.5) -> Image.Image:
    """Simulate thermal paper fading (receipts)."""
    arr = np.array(img).astype(float)
    h, w = arr.shape[:2]

    # Gradient fade from bottom to top
    fade = np.linspace(1 - intensity, 1, h).reshape(-1, 1, 1)
    arr = arr * fade + 255 * (1 - fade)

    # Add yellow tint
    yellow_tint = np.array([1.0, 0.95, 0.85])
    arr = arr * yellow_tint

    # Reduce contrast
    arr = (arr - 128) * 0.7 + 128

    # Random character dropout (simulate completely faded chars)
    dropout_mask = np.random.random((h, w, 1)) > (1 - intensity * 0.1)
    arr = np.where(dropout_mask, 255, arr)

    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def apply_photocopy_chain(img: Image.Image, generations: int = 3) -> Image.Image:
    """Simulate multiple photocopy generations."""
    result = img.copy()

    for gen in range(generations):
        # Increase contrast
        enhancer = ImageEnhance.Contrast(result)
        result = enhancer.enhance(1.2)

        # Add slight noise
        arr = np.array(result).astype(float)
        noise = np.random.normal(0, 5, arr.shape)
        arr = np.clip(arr + noise, 0, 255)
        result = Image.fromarray(arr.astype(np.uint8))

        # Add slight rotation
        angle = random.uniform(-1, 1)
        result = result.rotate(angle, fillcolor='white', expand=False)

        # Add toner specks
        draw = ImageDraw.Draw(result)
        for _ in range(gen * 5):
            x, y = random.randint(0, result.width), random.randint(0, result.height)
            draw.ellipse([x, y, x + 2, y + 2], fill='black')

    return result


def apply_crumpled_severe(img: Image.Image) -> Image.Image:
    """Severe crumple with fold lines and shadows."""
    result = img.copy()
    draw = ImageDraw.Draw(result)
    w, h = result.size

    # Major fold lines
    for _ in range(4):
        x1, y1 = random.randint(0, w), random.randint(0, h)
        x2, y2 = random.randint(0, w), random.randint(0, h)
        draw.line([(x1, y1), (x2, y2)], fill=(150, 150, 150), width=3)

    # Shadow regions near folds
    arr = np.array(result).astype(float)
    for _ in range(6):
        cx, cy = random.randint(0, w), random.randint(0, h)
        radius = random.randint(10, 30)

        y, x = np.ogrid[:h, :w]
        mask = ((x - cx) ** 2 + (y - cy) ** 2) < radius ** 2
        arr[mask] = arr[mask] * 0.85

    # Texture distortion (wrinkle shadows)
    for _ in range(10):
        x = random.randint(0, w - 15)
        y = random.randint(0, h - 15)
        draw.ellipse([x, y, x + random.randint(5, 15), y + random.randint(5, 15)],
                     fill=(200, 200, 200))

    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


# =============================================================================
# TIER 3: Multi-Layer Combination Attacks
# =============================================================================

def apply_phone_photo_bad_lighting(img: Image.Image) -> Image.Image:
    """Simulate rushed phone photo in dim room."""
    result = img.copy()

    # Random rotation (-15 to 15)
    angle = random.uniform(-15, 15)
    result = result.rotate(angle, fillcolor='white', expand=True)

    # Perspective skew
    w, h = result.size
    coeffs = [
        1.05, random.uniform(0.05, 0.1), -w * 0.03,
        random.uniform(0.02, 0.05), 1.05, -h * 0.03,
        0.0001, 0.0001
    ]
    result = result.transform((w, h), Image.PERSPECTIVE, coeffs, Image.BICUBIC, fillcolor='white')

    # Motion blur
    result = apply_motion_blur(result, length=random.randint(5, 12), angle=random.randint(0, 180))

    # Low brightness
    enhancer = ImageEnhance.Brightness(result)
    result = enhancer.enhance(random.uniform(0.5, 0.7))

    # Noise
    arr = np.array(result)
    noise = np.random.normal(0, random.randint(15, 30), arr.shape)
    arr = np.clip(arr + noise, 0, 255)
    result = Image.fromarray(arr.astype(np.uint8))

    # JPEG compression
    buffer = BytesIO()
    result.save(buffer, format='JPEG', quality=random.randint(40, 60))
    buffer.seek(0)
    result = Image.open(buffer).convert('RGB')

    return result


def apply_old_damaged_receipt(img: Image.Image) -> Image.Image:
    """Simulate 6-month old receipt from wallet."""
    result = img.copy()

    # Thermal fade
    result = apply_thermal_fade(result, intensity=0.6)

    # Crumple
    result = apply_crumpled_severe(result)

    # Low contrast
    enhancer = ImageEnhance.Contrast(result)
    result = enhancer.enhance(0.5)

    # Fold lines
    draw = ImageDraw.Draw(result)
    w, h = result.size

    # Horizontal fold (tri-fold)
    draw.line([(0, h // 3), (w, h // 3)], fill=(180, 180, 180), width=2)
    draw.line([(0, 2 * h // 3), (w, 2 * h // 3)], fill=(180, 180, 180), width=2)

    # Vertical fold
    draw.line([(w // 2, 0), (w // 2, h)], fill=(180, 180, 180), width=2)

    return result


def apply_archive_document(img: Image.Image) -> Image.Image:
    """Simulate 50-year-old scanned document."""
    result = img.copy()
    arr = np.array(result).astype(float)
    h, w = arr.shape[:2]

    # Yellowing
    yellow_tint = np.array([1.0, 0.92, 0.80])
    arr = arr * yellow_tint

    # Foxing spots (age spots)
    for _ in range(random.randint(5, 15)):
        cx, cy = random.randint(0, w), random.randint(0, h)
        radius = random.randint(3, 8)

        y, x = np.ogrid[:h, :w]
        mask = ((x - cx) ** 2 + (y - cy) ** 2) < radius ** 2
        arr[mask] = arr[mask] * np.array([0.85, 0.75, 0.65])

    # Ink fade (reduce black intensity)
    dark_mask = np.mean(arr, axis=2) < 100
    arr[dark_mask] = arr[dark_mask] * 0.7 + 50

    # Paper texture
    texture = np.random.normal(0, 5, (h, w, 1))
    arr = arr + texture

    result = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    # Slight blur (scanner artifact)
    result = result.filter(ImageFilter.GaussianBlur(radius=0.5))

    return result


def apply_night_flash(img: Image.Image) -> Image.Image:
    """Simulate flash photo at night with glare."""
    result = img.copy()

    # Vignette
    result = apply_vignette(result, strength=0.6)

    # Central overexposure (flash)
    arr = np.array(result).astype(float)
    h, w = arr.shape[:2]

    y, x = np.ogrid[:h, :w]
    center_y, center_x = h // 2, w // 2
    dist = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
    max_dist = min(center_x, center_y)

    # Overexposure in center
    exposure = 1 + 0.5 * np.maximum(0, 1 - dist / max_dist)
    exposure = exposure.reshape(h, w, 1)
    arr = arr * exposure

    # High contrast
    arr = (arr - 128) * 1.5 + 128

    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


# =============================================================================
# EXTREME DEGRADATIONS (Push models to 85% or lower)
# =============================================================================

def apply_ultimate_stress(img: Image.Image) -> Image.Image:
    """The ultimate stress test combining everything."""
    result = img.copy()

    # Start with motion blur
    result = apply_motion_blur(result, length=10, angle=random.randint(0, 180))

    # Add rotation
    result = result.rotate(random.uniform(-20, 20), fillcolor='white', expand=True)

    # Heavy noise
    arr = np.array(result)
    noise = np.random.normal(0, 40, arr.shape)
    arr = np.clip(arr + noise, 0, 255)
    result = Image.fromarray(arr.astype(np.uint8))

    # Uneven lighting
    result = apply_uneven_lighting(result, "shadow_band")

    # Reduce contrast
    enhancer = ImageEnhance.Contrast(result)
    result = enhancer.enhance(0.4)

    # Heavy JPEG compression
    buffer = BytesIO()
    result.save(buffer, format='JPEG', quality=15)
    buffer.seek(0)
    result = Image.open(buffer).convert('RGB')

    return result


# =============================================================================
# DEGRADATION REGISTRY
# =============================================================================

EXTREME_DEGRADATIONS = {
    # Tier 1: Enhanced single effects
    "motion_blur_light": DegradationConfig(
        name="motion_blur_light",
        description="Light motion blur (camera shake)",
        severity="mild",
        params={"func": apply_motion_blur, "length": 8, "angle": 45}
    ),
    "motion_blur_heavy": DegradationConfig(
        name="motion_blur_heavy",
        description="Heavy motion blur",
        severity="moderate",
        params={"func": apply_motion_blur, "length": 15, "angle": 0}
    ),
    "defocus_light": DegradationConfig(
        name="defocus_light",
        description="Light defocus blur",
        severity="mild",
        params={"func": apply_defocus_blur, "radius": 3}
    ),
    "defocus_heavy": DegradationConfig(
        name="defocus_heavy",
        description="Heavy defocus blur",
        severity="moderate",
        params={"func": apply_defocus_blur, "radius": 6}
    ),
    "film_grain": DegradationConfig(
        name="film_grain",
        description="Film grain noise",
        severity="mild",
        params={"func": apply_film_grain, "intensity": 0.2}
    ),
    "speckle_noise": DegradationConfig(
        name="speckle_noise",
        description="Speckle noise",
        severity="moderate",
        params={"func": apply_speckle_noise, "intensity": 0.15}
    ),
    "uneven_lighting_gradient": DegradationConfig(
        name="uneven_lighting_gradient",
        description="Uneven lighting (gradient)",
        severity="mild",
        params={"func": apply_uneven_lighting, "pattern": "gradient_lr"}
    ),
    "uneven_lighting_spotlight": DegradationConfig(
        name="uneven_lighting_spotlight",
        description="Uneven lighting (spotlight)",
        severity="moderate",
        params={"func": apply_uneven_lighting, "pattern": "spotlight"}
    ),
    "vignette": DegradationConfig(
        name="vignette",
        description="Vignette effect",
        severity="mild",
        params={"func": apply_vignette, "strength": 0.5}
    ),

    # Tier 2: Real-world damage
    "water_damage": DegradationConfig(
        name="water_damage",
        description="Water damage with stains",
        severity="severe",
        params={"func": apply_water_damage, "intensity": 0.4}
    ),
    "thermal_fade": DegradationConfig(
        name="thermal_fade",
        description="Thermal paper fading",
        severity="moderate",
        params={"func": apply_thermal_fade, "intensity": 0.5}
    ),
    "photocopy_chain": DegradationConfig(
        name="photocopy_chain",
        description="3rd generation photocopy",
        severity="moderate",
        params={"func": apply_photocopy_chain, "generations": 3}
    ),
    "crumpled_severe": DegradationConfig(
        name="crumpled_severe",
        description="Severely crumpled document",
        severity="severe",
        params={"func": apply_crumpled_severe}
    ),

    # Tier 3: Multi-layer combos
    "phone_photo_bad": DegradationConfig(
        name="phone_photo_bad",
        description="Phone photo in bad lighting",
        severity="severe",
        params={"func": apply_phone_photo_bad_lighting}
    ),
    "old_receipt": DegradationConfig(
        name="old_receipt",
        description="Old damaged receipt",
        severity="severe",
        params={"func": apply_old_damaged_receipt}
    ),
    "archive_doc": DegradationConfig(
        name="archive_doc",
        description="50-year-old archive document",
        severity="severe",
        params={"func": apply_archive_document}
    ),
    "night_flash": DegradationConfig(
        name="night_flash",
        description="Night flash photography",
        severity="moderate",
        params={"func": apply_night_flash}
    ),

    # Extreme stress
    "ultimate_stress": DegradationConfig(
        name="ultimate_stress",
        description="Ultimate stress test (all combined)",
        severity="extreme",
        params={"func": apply_ultimate_stress}
    ),
}


def apply_degradation(img: Image.Image, config: DegradationConfig) -> Image.Image:
    """Apply a degradation using its configuration."""
    func = config.params.get("func")
    if func is None:
        return img

    # Extract function arguments (exclude 'func' key)
    kwargs = {k: v for k, v in config.params.items() if k != "func"}

    return func(img, **kwargs)


def get_degradation_names() -> list:
    """Get list of all degradation names."""
    return list(EXTREME_DEGRADATIONS.keys())


def get_degradations_by_severity(severity: str) -> list:
    """Get degradations filtered by severity level."""
    return [
        name for name, config in EXTREME_DEGRADATIONS.items()
        if config.severity == severity
    ]
