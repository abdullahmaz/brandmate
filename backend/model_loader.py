"""
Lazy model loader: LLM is loaded at startup and kept in memory.
Image and Text models load on first use and are offloaded after use to free VRAM/RAM.
Uses per-component locks to avoid double-loading. Device placement is read from env.
"""
import os
import gc
import threading
from typing import Optional, Tuple, Any

# Lazy holder state
STATUS_UNLOADED = "unloaded"
STATUS_LOADING = "loading"
STATUS_READY = "ready"
STATUS_FAILED = "failed"


def _device_from_env(name: str) -> str:
    """Read device from MODEL_<NAME>_DEVICE env var. Falls back to 'cpu' if not set or invalid."""
    key = f"MODEL_{name}_DEVICE"
    val = os.getenv(key, "").strip().lower()
    if val in ("cuda", "cpu"):
        return val
    # Env var missing or invalid — warn and default to cpu so the server still starts.
    print(f"[model_loader] WARNING: {key} not set or invalid (got '{val}'). Defaulting to 'cpu'.")
    return "cpu"


def _llm_device() -> str:
    return _device_from_env("LLM")


def _image_device() -> str:
    return _device_from_env("IMAGE")


def _text_device() -> str:
    return _device_from_env("TEXT")


def _website_device() -> str:
    return _device_from_env("WEBSITE")


class _LazyHolder:
    def __init__(self, name: str, loader_fn):
        self.name = name
        self.loader_fn = loader_fn
        self.instance: Optional[Any] = None
        self.status = STATUS_UNLOADED
        self._lock = threading.Lock()

    def get(self) -> Tuple[Optional[Any], str]:
        with self._lock:
            if self.status == STATUS_READY:
                return (self.instance, STATUS_READY)
            if self.status == STATUS_FAILED:
                return (None, STATUS_FAILED)
            if self.status == STATUS_LOADING:
                return (None, STATUS_LOADING)
            # unloaded: start load
            self.status = STATUS_LOADING
        try:
            inst = self.loader_fn()
            with self._lock:
                if inst is not None:
                    self.instance = inst
                    self.status = STATUS_READY
                    return (inst, STATUS_READY)
                self.status = STATUS_FAILED
                return (None, STATUS_FAILED)
        except Exception as e:
            print(f"Error loading {self.name}: {e}")
            with self._lock:
                self.status = STATUS_FAILED
                return (None, STATUS_FAILED)

    def offload(self) -> None:
        """Release the loaded instance and free memory. Only call when done using the model."""
        with self._lock:
            if self.status != STATUS_READY:
                return
            self.instance = None
            self.status = STATUS_UNLOADED
        try:
            gc.collect()
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        print(f"[model_loader] {self.name} offloaded.")


def _load_llm():
    from llm_orchestrator import LLMOrchestrator
    device = _llm_device()
    return LLMOrchestrator(device=device)


def _load_image_generator():
    from generators.image_generator import ImageGenerator
    device = _image_device()
    return ImageGenerator(device=device)


def _load_text_generator():
    from generators.text_generator import TextGenerator
    device = _text_device()
    return TextGenerator(device=device)


def _load_website_generator():
    from generators.website_generator import WebsiteGenerator
    device = _website_device()
    return WebsiteGenerator(device=device)


_llm_holder = _LazyHolder("LLM", _load_llm)
_image_holder = _LazyHolder("ImageGenerator", _load_image_generator)
_text_holder = _LazyHolder("TextGenerator", _load_text_generator)
_website_holder = _LazyHolder("WebsiteGenerator", _load_website_generator)


def get_llm() -> Tuple[Optional[Any], str]:
    """Return (llm_orchestrator_or_none, status). status is 'ready' | 'loading' | 'failed'."""
    return _llm_holder.get()


def get_image_generator() -> Tuple[Optional[Any], str]:
    """Return (image_generator_or_none, status). status is 'ready' | 'loading' | 'failed'."""
    return _image_holder.get()


def get_text_generator() -> Tuple[Optional[Any], str]:
    """Return (text_generator_or_none, status). status is 'ready' | 'loading' | 'failed'."""
    return _text_holder.get()


def get_website_generator() -> Tuple[Optional[Any], str]:
    """Return (website_generator_or_none, status). status is 'ready' | 'loading' | 'failed'."""
    return _website_holder.get()


def get_model_status() -> dict:
    """Return current status of all models for diagnostics."""
    with _llm_holder._lock:
        llm_s = _llm_holder.status
    with _image_holder._lock:
        img_s = _image_holder.status
    with _text_holder._lock:
        txt_s = _text_holder.status
    with _website_holder._lock:
        web_s = _website_holder.status
    return {"llm": llm_s, "image": img_s, "text": txt_s, "website": web_s}


def offload_image_generator() -> None:
    """Offload image model after use to free VRAM/RAM. LLM stays loaded."""
    _image_holder.offload()


def offload_text_generator() -> None:
    """Offload text model after use to free VRAM/RAM. LLM stays loaded."""
    _text_holder.offload()


def load_llm_at_startup() -> None:
    """Call at server startup to load the LLM so it is always ready. Run in background thread."""
    get_llm()
