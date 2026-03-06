import asyncio
import base64
import copy
import json
import os
import random
import time
import websocket  # pip install websocket-client
from pathlib import Path
from typing import Optional

import httpx

COMFYUI_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
COMFYUI_CLIENT_ID = "brandmate_comfyui_session"  # fixed so ComfyUI keeps models loaded
WORKFLOWS_DIR = Path(__file__).parent / "workflows"

# ── Node IDs (from exported workflow JSONs) ────────────────────────────────
# T2V: wan2.1_t2v.json
T2V_POSITIVE_NODE = "6"   # CLIPTextEncode – positive prompt
T2V_SEED_NODE     = "3"   # KSampler        – seed

# I2V: wan2.1_i2b_fun_1.4b.json
I2V_POSITIVE_NODE = "6"   # CLIPTextEncode – positive prompt
I2V_IMAGE_NODE    = "52"  # LoadImage       – image filename
I2V_SEED_NODE     = "3"   # KSampler        – seed
# ──────────────────────────────────────────────────────────────────────────


class VideoGenerator:
    def __init__(self):
        self.comfyui_url = COMFYUI_URL
        self._t2v_workflow = self._load_workflow("wan2.1_t2v.json")
        self._i2v_workflow = self._load_workflow("wan2.1_i2b_fun_1.4b.json")
        self.model_loaded = True  # ComfyUI manages its own model lifecycle

    # ── Internal helpers ───────────────────────────────────────────────────

    def _load_workflow(self, filename: str) -> dict:
        path = WORKFLOWS_DIR / filename
        with open(path) as f:
            return json.load(f)

    async def _upload_image_to_comfyui(
        self, image_bytes: bytes, filename: str = "brandmate_input.jpg"
    ) -> str:
        """Upload image bytes to ComfyUI /upload/image. Returns the filename ComfyUI assigned."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.comfyui_url}/upload/image",
                files={"image": (filename, image_bytes, "image/jpeg")},
                data={"overwrite": "true"},
            )
            response.raise_for_status()
            assigned_name = response.json()["name"]
            print(f"DEBUG: Image uploaded to ComfyUI as '{assigned_name}'")
            return assigned_name

    async def _queue_prompt(self, workflow: dict) -> str:
        """POST workflow to ComfyUI /prompt. Returns prompt_id."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.comfyui_url}/prompt",
                json={"prompt": workflow, "client_id": COMFYUI_CLIENT_ID},
            )
            response.raise_for_status()
            prompt_id = response.json()["prompt_id"]
            print(f"DEBUG: Workflow queued, prompt_id={prompt_id}")
            return prompt_id

    async def _wait_for_result(
        self, prompt_id: str, timeout: int = 600
    ) -> Optional[str]:
        """
        Wait for ComfyUI completion via WebSocket (same approach as working streamlit app).
        Then look up filename from /history targeting node 28 (SaveAnimatedWEBP) directly.
        """
        comfy_addr = self.comfyui_url.replace("http://", "").replace("https://", "")
        ws_url = f"ws://{comfy_addr}/ws?clientId={COMFYUI_CLIENT_ID}"

        def _listen_ws():
            """Blocking WS listener — runs in thread pool to avoid blocking event loop."""
            ws = websocket.WebSocket()
            ws.settimeout(timeout)
            ws.connect(ws_url)
            print(f"DEBUG: WebSocket connected, waiting for prompt_id={prompt_id}")
            while True:
                out = ws.recv()
                if isinstance(out, str):
                    message = json.loads(out)
                    if (
                        message.get("type") == "executing"
                        and message["data"].get("node") is None
                        and message["data"].get("prompt_id") == prompt_id
                    ):
                        print("DEBUG: ComfyUI generation complete!")
                        ws.close()
                        return True
            return False

        # Run blocking WS in thread pool so we don't block FastAPI event loop
        loop = asyncio.get_event_loop()
        try:
            await asyncio.wait_for(
                loop.run_in_executor(None, _listen_ws),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            print("DEBUG: WebSocket wait timed out")
            return None

        # Small buffer for file writing (same as working app)
        await asyncio.sleep(2)

        # Look up filename from history — target node 28 (SaveAnimatedWEBP) directly
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.comfyui_url}/history/{prompt_id}")
                history_response = resp.json()
                if prompt_id in history_response:
                    outputs = history_response[prompt_id].get("outputs", {})
                    node_output = outputs.get("28", {})
                    print(f"DEBUG: Node 28 output: {node_output}")
                    for key in ("gifs", "images", "animated", "webp"):
                        if key in node_output and isinstance(node_output[key], list):
                            filename = node_output[key][0]["filename"]
                            print(f"DEBUG: Output file ready: {filename}")
                            return filename
        except Exception as e:
            print(f"DEBUG: History lookup failed: {e}")

        return None

    async def _fetch_as_base64(self, filename: str) -> str:
        """Fetch generated video from ComfyUI /view and return as base64 data URI."""
        url = f"{self.comfyui_url}/view?filename={filename}&type=output"
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(url)
            response.raise_for_status()
            b64 = base64.b64encode(response.content).decode()
            return f"data:image/webp;base64,{b64}"

    # ── Public API ─────────────────────────────────────────────────────────

    async def generate_t2v(
        self, prompt: str, video_type: str = "promotional"
    ) -> str:
        """
        Text-to-video.
        Injects prompt + random seed into the T2V workflow, queues it,
        waits for completion, and returns a base64 WEBP data URI.
        """
        workflow = copy.deepcopy(self._t2v_workflow)

        workflow[T2V_POSITIVE_NODE]["inputs"]["text"] = prompt
        workflow[T2V_SEED_NODE]["inputs"]["seed"] = random.randint(0, 2**32 - 1)

        prompt_id = await self._queue_prompt(workflow)
        filename = await self._wait_for_result(prompt_id)
        if not filename:
            raise RuntimeError("T2V generation timed out or failed")

        return await self._fetch_as_base64(filename)

    async def generate_i2v(
        self,
        prompt: str,
        image_bytes: bytes,
        image_filename: str = "brandmate_input.jpg",
        video_type: str = "promotional",
    ) -> str:
        """
        Image-to-video.
        Uploads the image to ComfyUI, injects prompt + image + random seed
        into the I2V workflow, queues it, waits, and returns a base64 WEBP data URI.
        """
        comfy_image_name = await self._upload_image_to_comfyui(
            image_bytes, image_filename
        )

        workflow = copy.deepcopy(self._i2v_workflow)

        workflow[I2V_POSITIVE_NODE]["inputs"]["text"] = prompt
        workflow[I2V_IMAGE_NODE]["inputs"]["image"] = comfy_image_name
        workflow[I2V_SEED_NODE]["inputs"]["seed"] = random.randint(0, 2**32 - 1)

        prompt_id = await self._queue_prompt(workflow)
        filename = await self._wait_for_result(prompt_id)
        if not filename:
            raise RuntimeError("I2V generation timed out or failed")

        return await self._fetch_as_base64(filename)