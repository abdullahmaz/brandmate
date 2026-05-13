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
I2V_POSITIVE_NODE = "6"   # CLIPTextEncode – positive prompt
I2V_IMAGE_NODE    = "52"  # LoadImage       – image filename
I2V_SEED_NODE     = "3"   # KSampler        – seed
