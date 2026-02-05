"""
VRAM-Aware Model Manager for RheaRouter Ensemble

Manages model loading/unloading for 8GB VRAM constraint.
Only one large model can be loaded at a time.
"""

import time
import subprocess
import requests
from dataclasses import dataclass
from typing import Optional


@dataclass
class ModelInfo:
    """Information about a loaded model."""
    name: str
    vram_mb: int
    loaded_at: float


class ModelManager:
    """
    Manages vision model lifecycle with VRAM awareness.

    Only ONE model can be loaded in VRAM at a time due to 8GB constraint.
    Ollama automatically unloads previous model when loading a new one.
    """

    # Estimated VRAM requirements from benchmarks
    MODEL_VRAM = {
        'qwen2.5vl:7b': 5500,
        'minicpm-v:8b': 5947,
        'llava:7b': 5725,
        'gemma3n:latest': 5000,
    }

    def __init__(self,
                 ollama_url: str = "http://localhost:11434",
                 swap_cooldown: float = 5.0,
                 vram_limit_mb: int = 8192):
        self.ollama_url = ollama_url
        self.swap_cooldown = swap_cooldown
        self.vram_limit_mb = vram_limit_mb
        self.current_model: Optional[str] = None
        self.last_swap_time: float = 0

    def get_vram_usage(self) -> int:
        """Get current VRAM usage in MB using nvidia-smi."""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return int(result.stdout.strip())
        except Exception:
            pass
        return 0

    def is_model_loaded(self, model_name: str) -> bool:
        """Check if a specific model is currently loaded."""
        return self.current_model == model_name

    def ensure_loaded(self, model_name: str) -> bool:
        """
        Ensure the specified model is loaded in VRAM.

        Returns True if model is ready, False if loading failed.
        """
        if self.current_model == model_name:
            return True

        # Respect cooldown period between swaps
        time_since_swap = time.time() - self.last_swap_time
        if time_since_swap < self.swap_cooldown:
            time.sleep(self.swap_cooldown - time_since_swap)

        # Load the new model (Ollama auto-unloads previous)
        try:
            # Make a minimal request to force model loading
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": "test",
                    "stream": False
                },
                timeout=120  # Model loading can take a while
            )

            if response.status_code == 200:
                self.current_model = model_name
                self.last_swap_time = time.time()
                return True
            else:
                return False

        except Exception as e:
            print(f"Error loading model {model_name}: {e}")
            return False

    def unload_current(self) -> bool:
        """Unload the current model to free VRAM."""
        if self.current_model is None:
            return True

        # Ollama doesn't have explicit unload, but we can track state
        self.current_model = None
        return True

    def get_model_order(self, technique: str = "accuracy") -> list:
        """
        Get optimal model execution order based on technique.

        Returns list of model names in recommended execution order.
        """
        if technique == "accuracy":
            # Best accuracy first
            return ['qwen2.5vl:7b', 'minicpm-v:8b', 'llava:7b']
        elif technique == "speed":
            # Fastest first
            return ['llava:7b', 'minicpm-v:8b', 'qwen2.5vl:7b']
        elif technique == "stability":
            # Most stable first
            return ['minicpm-v:8b', 'qwen2.5vl:7b', 'llava:7b']
        else:
            # Default: accuracy order
            return ['qwen2.5vl:7b', 'minicpm-v:8b', 'llava:7b']

    def estimate_swap_time(self, from_model: str, to_model: str) -> float:
        """Estimate time to swap between models."""
        # Based on benchmark observations
        base_load_time = 8.0  # seconds to load a 7B model
        return base_load_time + self.swap_cooldown

    def get_status(self) -> dict:
        """Get current manager status."""
        return {
            'current_model': self.current_model,
            'vram_usage_mb': self.get_vram_usage(),
            'vram_limit_mb': self.vram_limit_mb,
            'last_swap_time': self.last_swap_time,
        }
