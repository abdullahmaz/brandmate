import asyncio
import base64
import copy
import json
import os
import random
import shutil
import time
import urllib.request
import websocket  
from pathlib import Path
from typing import Optional
import httpx

from config import (
    COMFYUI_URL,
    COMFYUI_ADDR,
    COMFYUI_CLIENT_ID,
    COMFYUI_OUTPUT_PATH,
    LOCAL_VIDEO_DIR,
    WORKFLOWS_DIR,
    T2V_POSITIVE_NODE,
    T2V_SEED_NODE,
    I2V_POSITIVE_NODE,
    I2V_IMAGE_NODE,
    I2V_SEED_NODE,
)

class VideoGenerator:
    def __init__(self):
        self.comfyui_url = COMFYUI_URL
        self._t2v_workflow = self._load_workflow("wan2.1_t2v.json")
        self._i2v_workflow = self._load_workflow("wan2.1_i2b_fun_1.4b.json")
        self.model_loaded = True  # ComfyUI manages its own model lifecycle

        # Local folder to copy generated videos into
        os.makedirs(LOCAL_VIDEO_DIR, exist_ok=True)

    def _load_workflow(self, filename: str) -> dict:
        path = WORKFLOWS_DIR / filename
        with open(path) as f:
            return json.load(f)

    def _upload_image_sync(self, image_bytes: bytes, filename: str = "brandmate_input.jpg") -> str:
        "Upload image to ComfyUI synchronously"
        import requests
        files = {"image": (filename, image_bytes, "image/jpeg")}
        response = requests.post(f"{self.comfyui_url}/upload/image", files=files)
        response.raise_for_status()
        assigned_name = response.json()["name"]
        print(f"DEBUG: Image uploaded to ComfyUI as '{assigned_name}'")
        return assigned_name

    def _generate_sync(self, workflow: dict) -> Optional[str]:
        # 1. Connect WebSocket
        ws = websocket.WebSocket()
        ws.connect(f"ws://{COMFYUI_ADDR}/ws?clientId={COMFYUI_CLIENT_ID}")

        # 2. Queue prompt
        print("DEBUG: Sending prompt to ComfyUI...")
        p = {"prompt": workflow, "client_id": COMFYUI_CLIENT_ID}
        data = json.dumps(p).encode("utf-8")
        req = urllib.request.Request(f"{self.comfyui_url}/prompt", data=data)
        prompt_id = json.loads(urllib.request.urlopen(req).read())["prompt_id"]
        print(f"DEBUG: Workflow queued, prompt_id={prompt_id}")

        # 3. Wait for completion via WebSocket
        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if (
                    message["type"] == "executing"
                    and message["data"]["node"] is None
                    and message["data"]["prompt_id"] == prompt_id
                ):
                    print("DEBUG: ComfyUI generation complete!")
                    break
        ws.close()

        # 4. Lookup filename from history — target node 28 (SaveAnimatedWEBP)
        time.sleep(2)  # buffer for file writing
        video_filename = None
        try:
            with urllib.request.urlopen(f"{self.comfyui_url}/history/{prompt_id}") as res:
                history_response = json.loads(res.read())
                if prompt_id in history_response:
                    history = history_response[prompt_id]
                    if "outputs" in history and "28" in history["outputs"]:
                        node_output = history["outputs"]["28"]
                        for key in ["gifs", "images", "animated", "webp"]:
                            if key in node_output:
                                video_filename = node_output[key][0]["filename"]
                                break
        except Exception as e:
            print(f"DEBUG: History lookup failed: {e}")

        if not video_filename:
            print("DEBUG: Could not find output filename in history")
            return None

        # 5. Copy file to local folder
        src_path = os.path.join(COMFYUI_OUTPUT_PATH, video_filename)
        dst_path = os.path.join(LOCAL_VIDEO_DIR, video_filename)
        if os.path.exists(src_path):
            shutil.copy(src_path, dst_path)
            print(f"DEBUG: Video copied to: {dst_path}")
            return dst_path

        print(f"DEBUG: Source file not found: {src_path}")
        return None

    async def _run_generation(self, workflow: dict) -> str:
        """Run blocking _generate_sync in thread pool so FastAPI loop isn't blocked."""
        loop = asyncio.get_event_loop()
        local_path = await loop.run_in_executor(None, self._generate_sync, workflow)
        if not local_path:
            raise RuntimeError("Video generation failed or timed out")
        return local_path

    def _read_as_base64(self, file_path: str) -> str:
        """Read WEBP from disk and return as base64 data URI (same as streamlit app)."""
        with open(file_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f"data:image/webp;base64,{b64}"

    async def generate_t2v(self, prompt: str, video_type: str = "promotional") -> str:
        """Text-to-video — injects prompt into T2V workflow and returns base64 WEBP."""
        workflow = copy.deepcopy(self._t2v_workflow)
        workflow[T2V_POSITIVE_NODE]["inputs"]["text"] = prompt
        workflow[T2V_SEED_NODE]["inputs"]["seed"] = random.randint(0, 2**32 - 1)

        local_path = await self._run_generation(workflow)
        return self._read_as_base64(local_path)

    async def generate_i2v(
        self,
        prompt: str,
        image_bytes: bytes,
        image_filename: str = "brandmate_input.jpg",
        video_type: str = "promotional",
    ) -> str:
        """Image-to-video — uploads image, injects into I2V workflow, returns base64 WEBP."""
        loop = asyncio.get_event_loop()
        comfy_image_name = await loop.run_in_executor(
            None, self._upload_image_sync, image_bytes, image_filename
        )

        workflow = copy.deepcopy(self._i2v_workflow)
        workflow[I2V_POSITIVE_NODE]["inputs"]["text"] = prompt
        workflow[I2V_IMAGE_NODE]["inputs"]["image"] = comfy_image_name
        workflow[I2V_SEED_NODE]["inputs"]["seed"] = random.randint(0, 2**32 - 1)

        local_path = await self._run_generation(workflow)
        return self._read_as_base64(local_path)