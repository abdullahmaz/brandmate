import os
from pathlib import Path

LOCAL_VIDEO_DIR = os.path.join(os.path.dirname(__file__), "generated_videos")
WORKFLOWS_DIR = Path(__file__).parent / "workflows"

# Remote video service (primary).
VIDEO_BACKEND_TOKEN = os.getenv("VIDEO_BACKEND_TOKEN", "")
VIDEO_BACKEND_PROVIDER = os.getenv("VIDEO_BACKEND_PROVIDER", "")
VIDEO_BACKEND_T2V_MODEL = os.getenv("VIDEO_BACKEND_T2V_MODEL", "")
VIDEO_BACKEND_I2V_MODEL = os.getenv("VIDEO_BACKEND_I2V_MODEL", "")
VIDEO_BACKEND_TIMEOUT = int(os.getenv("VIDEO_BACKEND_TIMEOUT", "600"))

# Local video service (fallback). Used automatically when the remote service
# fails (out of credits, network error, auth error, etc.).
COMFYUI_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
COMFYUI_CLIENT_ID = "brandmate_comfyui_session"  # fixed so ComfyUI keeps models loaded

# Node IDs in the bundled ComfyUI workflows.
T2V_POSITIVE_NODE = "6"   # CLIPTextEncode – positive prompt
T2V_SEED_NODE     = "3"   # KSampler        – seed
T2V_LENGTH_NODE   = "40"  # EmptyHunyuanLatentVideo – frame count (length)
I2V_POSITIVE_NODE = "6"   # CLIPTextEncode – positive prompt
I2V_IMAGE_NODE    = "52"  # LoadImage       – image filename
I2V_SEED_NODE     = "3"   # KSampler        – seed
I2V_LENGTH_NODE   = "57"  # WanCameraEmbedding – frame count (length)
SAVE_NODE         = "28"  # SaveAnimatedWEBP – playback fps lives here

# Quality presets — all clips target ~6 seconds. Quality knob varies
# motion smoothness by changing both frame count and playback fps.
# Frame count must be 4n+1 for Wan 2.1: 49, 73, 97 all qualify.
VIDEO_QUALITY_PRESETS = {
    "speed":    {"frames": 49, "fps": 8},   # ~6s, choppier (matches today's default)
    "balanced": {"frames": 73, "fps": 12},  # ~6s, smooth
    "quality":  {"frames": 97, "fps": 16},  # ~6s, native fps, smoothest
}
VIDEO_QUALITY_DEFAULT = "balanced"
