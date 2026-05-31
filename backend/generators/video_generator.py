import asyncio
import base64
import copy
import json
import os
import random
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request

import websocket
from huggingface_hub import AsyncInferenceClient

from config import (
    VIDEO_BACKEND_TOKEN,
    VIDEO_BACKEND_PROVIDER,
    VIDEO_BACKEND_T2V_MODEL,
    VIDEO_BACKEND_I2V_MODEL,
    VIDEO_BACKEND_TIMEOUT,
    COMFYUI_URL,
    COMFYUI_CLIENT_ID,
    LOCAL_VIDEO_DIR,
    WORKFLOWS_DIR,
    T2V_POSITIVE_NODE,
    T2V_SEED_NODE,
    T2V_LENGTH_NODE,
    I2V_POSITIVE_NODE,
    I2V_IMAGE_NODE,
    I2V_SEED_NODE,
    I2V_LENGTH_NODE,
    SAVE_NODE,
    VIDEO_QUALITY_PRESETS,
    VIDEO_QUALITY_DEFAULT,
)


def _preset_for(quality_mode: str) -> dict:
    return VIDEO_QUALITY_PRESETS.get(quality_mode, VIDEO_QUALITY_PRESETS[VIDEO_QUALITY_DEFAULT])


_PROMPT_PREFIX = (
    "Modest, fully-covered traditional Eastern clothing only "
    "(shalwar kameez, kurta, lawn suit, lehenga with full dupatta coverage). "
    "Conservative, family-friendly, professional fashion content. "
    "No skin exposure, no revealing or suggestive imagery. "
)

_NEGATIVE_PROMPT = (
    "nudity, nsfw, revealing clothing, bikini, lingerie, swimwear, cleavage, "
    "bare shoulders, midriff, short skirt, tight clothing, western dress, "
    "low-cut, sexual, suggestive, exposed skin"
)


def _guess_mime(video_bytes: bytes) -> str:
    head = video_bytes[:32]
    if b"ftyp" in head:
        return "video/mp4"
    if head.startswith(b"RIFF") and b"WEBP" in head[:16]:
        return "image/webp"
    return "video/mp4"


def _to_data_uri(video_bytes: bytes) -> str:
    mime = _guess_mime(video_bytes)
    return f"data:{mime};base64,{base64.b64encode(video_bytes).decode()}"


class _RemoteBackend:
    """Calls a hosted video service via HF Inference Providers."""

    def __init__(self):
        self._t2v_model = VIDEO_BACKEND_T2V_MODEL
        self._i2v_model = VIDEO_BACKEND_I2V_MODEL
        self._client = AsyncInferenceClient(
            provider=VIDEO_BACKEND_PROVIDER or None,
            api_key=VIDEO_BACKEND_TOKEN or None,
            timeout=VIDEO_BACKEND_TIMEOUT,
        )

    @property
    def configured(self) -> bool:
        return bool(VIDEO_BACKEND_TOKEN and self._t2v_model and self._i2v_model)

    async def text_to_video(self, prompt: str, preset: dict) -> bytes:
        # Cloud only takes num_frames; playback fps is provider-controlled,
        # so durations on cloud may differ from local (which encodes the fps
        # directly into the WEBP).
        return await self._client.text_to_video(
            prompt,
            model=self._t2v_model,
            negative_prompt=_NEGATIVE_PROMPT,
            num_frames=preset["frames"],
        )

    async def image_to_video(self, prompt: str, image_bytes: bytes, preset: dict) -> bytes:
        return await self._client.image_to_video(
            image_bytes,
            prompt=prompt,
            model=self._i2v_model,
            negative_prompt=_NEGATIVE_PROMPT,
            num_frames=preset["frames"],
        )


class _LocalBackend:
    """Calls a locally-running ComfyUI instance using the bundled workflows."""

    def __init__(self):
        self._url = COMFYUI_URL
        self._workflows_loaded = False
        try:
            self._t2v_workflow = self._load_workflow("wan2.1_t2v.json")
            self._i2v_workflow = self._load_workflow("wan2.1_i2b_fun_1.4b.json")
            self._workflows_loaded = True
        except Exception as e:
            print(f"DEBUG: Local video backend workflow load failed: {e}")
        os.makedirs(LOCAL_VIDEO_DIR, exist_ok=True)

    @property
    def configured(self) -> bool:
        return self._workflows_loaded and bool(self._url)

    @staticmethod
    def _load_workflow(filename: str) -> dict:
        with open(WORKFLOWS_DIR / filename) as f:
            return json.load(f)

    def _upload_image_sync(self, image_bytes: bytes, filename: str = "brandmate_input.jpg") -> str:
        import requests
        files = {"image": (filename, image_bytes, "image/jpeg")}
        response = requests.post(f"{self._url}/upload/image", files=files)
        response.raise_for_status()
        return response.json()["name"]

    def _generate_sync(self, workflow: dict) -> bytes:
        ws_url = self._url.replace("https://", "wss://", 1).replace("http://", "ws://", 1)
        ws = websocket.WebSocket()
        ws.connect(f"{ws_url}/ws?clientId={COMFYUI_CLIENT_ID}")

        payload = json.dumps({"prompt": workflow, "client_id": COMFYUI_CLIENT_ID}).encode("utf-8")
        req = urllib.request.Request(f"{self._url}/prompt", data=payload)
        try:
            prompt_id = json.loads(urllib.request.urlopen(req).read())["prompt_id"]
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"ComfyUI rejected workflow ({e.code}): {body}") from e

        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if (
                    message["type"] == "executing"
                    and message["data"]["node"] is None
                    and message["data"]["prompt_id"] == prompt_id
                ):
                    break
        ws.close()

        time.sleep(2)
        with urllib.request.urlopen(f"{self._url}/history/{prompt_id}") as res:
            history = json.loads(res.read())[prompt_id]

        node_output = history.get("outputs", {}).get("28", {})
        entry = None
        for key in ("gifs", "images", "animated", "webp"):
            if key in node_output:
                entry = node_output[key][0]
                break
        if not entry:
            raise RuntimeError("Local video backend: no output found in workflow history.")

        view_url = f"{self._url}/view?{urllib.parse.urlencode({'filename': entry['filename'], 'subfolder': entry.get('subfolder', ''), 'type': entry.get('type', 'output')})}"
        local_path = os.path.join(LOCAL_VIDEO_DIR, entry["filename"])
        with urllib.request.urlopen(view_url) as res, open(local_path, "wb") as f:
            shutil.copyfileobj(res, f)

        with open(local_path, "rb") as f:
            return f.read()

    async def _run_workflow(self, workflow: dict) -> bytes:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._generate_sync, workflow)

    async def text_to_video(self, prompt: str, preset: dict) -> bytes:
        workflow = copy.deepcopy(self._t2v_workflow)
        workflow[T2V_POSITIVE_NODE]["inputs"]["text"] = prompt
        workflow[T2V_SEED_NODE]["inputs"]["seed"] = random.randint(0, 2**32 - 1)
        workflow[T2V_LENGTH_NODE]["inputs"]["length"] = preset["frames"]
        workflow[SAVE_NODE]["inputs"]["fps"] = preset["fps"]
        return await self._run_workflow(workflow)

    async def image_to_video(self, prompt: str, image_bytes: bytes, preset: dict) -> bytes:
        loop = asyncio.get_event_loop()
        comfy_image_name = await loop.run_in_executor(None, self._upload_image_sync, image_bytes)
        workflow = copy.deepcopy(self._i2v_workflow)
        workflow[I2V_POSITIVE_NODE]["inputs"]["text"] = prompt
        workflow[I2V_IMAGE_NODE]["inputs"]["image"] = comfy_image_name
        workflow[I2V_SEED_NODE]["inputs"]["seed"] = random.randint(0, 2**32 - 1)
        workflow[I2V_LENGTH_NODE]["inputs"]["length"] = preset["frames"]
        workflow[SAVE_NODE]["inputs"]["fps"] = preset["fps"]
        return await self._run_workflow(workflow)


class VideoGenerator:
    """Generates short videos. Tries the remote service first, falls back to a
    locally-running secondary if that fails (out of credit, network, auth, etc.).
    """

    def __init__(self):
        self._remote = _RemoteBackend()
        self._local = _LocalBackend()
        self.model_loaded = True

    @staticmethod
    def _prepare_prompt(prompt: str) -> str:
        return _PROMPT_PREFIX + prompt

    async def _with_fallback(self, remote_call, local_call) -> bytes:
        if self._remote.configured:
            try:
                return await remote_call()
            except Exception as e:
                if not self._local.configured:
                    raise
                print(f"DEBUG: Remote video backend failed ({e}); falling back to local.")
        if not self._local.configured:
            raise RuntimeError("Video service is not configured.")
        return await local_call()

    async def generate_t2v(
        self,
        prompt: str,
        video_type: str = "promotional",
        quality_mode: str = VIDEO_QUALITY_DEFAULT,
    ) -> str:
        prepared = self._prepare_prompt(prompt)
        preset = _preset_for(quality_mode)
        video_bytes = await self._with_fallback(
            lambda: self._remote.text_to_video(prepared, preset),
            lambda: self._local.text_to_video(prepared, preset),
        )
        return _to_data_uri(video_bytes)

    async def generate_i2v(
        self,
        prompt: str,
        image_bytes: bytes,
        image_filename: str = "brandmate_input.jpg",
        video_type: str = "promotional",
        quality_mode: str = VIDEO_QUALITY_DEFAULT,
    ) -> str:
        prepared = self._prepare_prompt(prompt)
        preset = _preset_for(quality_mode)
        video_bytes = await self._with_fallback(
            lambda: self._remote.image_to_video(prepared, image_bytes, preset),
            lambda: self._local.image_to_video(prepared, image_bytes, preset),
        )
        return _to_data_uri(video_bytes)
