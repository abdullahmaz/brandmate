import os
from pathlib import Path

COMFYUI_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
COMFYUI_ADDR = os.getenv("COMFYUI_ADDR", "127.0.0.1:8188")
COMFYUI_CLIENT_ID = "brandmate_comfyui_session"  # fixed so ComfyUI keeps models loaded
COMFYUI_OUTPUT_PATH = os.getenv("COMFYUI_OUTPUT_PATH", r"C:\Users\katri\Documents\ComfyUI\output")
LOCAL_VIDEO_DIR = os.path.join(os.path.dirname(__file__), "generated_videos")
WORKFLOWS_DIR = Path(__file__).parent / "workflows"

# ── Node IDs (from exported workflow JSONs)
# T2V: wan2.1_t2v.json
T2V_POSITIVE_NODE = "6"   # CLIPTextEncode – positive prompt
T2V_SEED_NODE     = "3"   # KSampler        – seed

# I2V: wan2.1_i2b_fun_1.4b.json
I2V_POSITIVE_NODE = "6"   # CLIPTextEncode – positive prompt
I2V_IMAGE_NODE    = "52"  # LoadImage       – image filename
I2V_SEED_NODE     = "3"   # KSampler        – seed