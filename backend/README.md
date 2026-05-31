# Brandmate backend

FastAPI service that hosts the LLM orchestrator and five generation tools (image, text,
video, website, billboard search). The LLM loads at startup and stays resident; image and
text models load lazily and swap VRAM so a single 8 GB GPU can host everything.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env          # add HF_TOKEN (required)
python main.py                # http://localhost:8000
```

Interactive docs at [`/docs`](http://localhost:8000/docs).

First run will pull ~10 GB of model weights from Hugging Face. Llama 3.2 and Qwen2.5 are
gated — accept their terms on the model page before running.

## Requirements

| Resource | Minimum | Recommended |
| -------- | ------- | ----------- |
| RAM      | 8 GB    | 16 GB+      |
| GPU VRAM | CPU OK  | 8 GB+ NVIDIA |
| Disk     | 15 GB   | 25 GB SSD   |
| Python   | 3.10    | 3.11        |

## Architecture

```
                       ┌─────────────────────┐
   User message ─────▶ │  LLM orchestrator   │  Llama 3.2 3B Instruct
                       │  (tool calling)     │
                       └─────────┬───────────┘
                                 │
        ┌───────────┬────────────┼────────────┬─────────────┐
        ▼           ▼            ▼            ▼             ▼
   image_gen   text_gen    video_gen    website_gen   billboard_search
   OpenJourney Qwen2.5+LoRA Wan 2.1     DeepSeek-V3   adbuq scraper
   (local SD)  (local)     (ComfyUI    (HF Inference) (httpx + BS4)
                            or remote)
```

Each tool is a thin wrapper around a model or external service. The orchestrator returns
JSON tool calls; `main.py` dispatches them, persists the result to Supabase, and uploads
binaries to S3 when configured.

### Model lifecycle

`model_loader.py` defines per-model `_LazyHolder` objects with `(get, offload)`:

- **LLM** — loaded at startup in a background thread, never offloaded.
- **Image** and **Text** generators — load on first call. Before loading one, the other is
  offloaded (`offload_text_generator()` before image; `offload_image_generator()` before
  text). Consecutive calls to the same generator stay warm.
- **Website generator** — uses the HF Inference router over HTTP, no local weights.
- **Video generator** — also network-bound (HF Inference primary, ComfyUI fallback).

Set device per model via `MODEL_*_DEVICE` env vars (see Configuration).

## Tools

| Tool                | Backing model              | Notes                                              |
| ------------------- | -------------------------- | -------------------------------------------------- |
| `image_generation`  | `prompthero/openjourney`   | 512×512, SD v1.5 base, "mdjrny-v4 style" prefix    |
| `text_generation`   | `Qwen/Qwen2.5-1.5B-Instruct` + LoRA | Fine-tuned for marketing copy, captions, outreach |
| `video_generation`  | Wan 2.1 (T2V / I2V)        | HF Inference primary, ComfyUI local fallback, quality presets |
| `website_generation`| `deepseek-ai/DeepSeek-V3`  | Via `router.huggingface.co`, returns full HTML     |
| `billboard_search`  | adbuq.com scraper          | Pakistani cities, OOH inventory + contact enrichment |

### Video pipeline notes

- **T2V** — pure text-to-video
- **I2V** — image-to-video. The LLM sets `use_reference_image=true` when the user refers
  to a previous image; `main.py` pulls the latest image S3 URL from the chat and feeds it
  back in. If the user attaches an image directly, that wins.
- **Quality presets** (`config.py`) — all ~6 seconds, different frame counts:

  | Preset     | Frames | FPS | Notes                       |
  | ---------- | ------ | --- | --------------------------- |
  | `speed`    | 49     | 8   | choppier, fastest           |
  | `balanced` | 73     | 12  | default, smooth             |
  | `quality`  | 97     | 16  | smoothest, longest to render |

### Billboard search notes

The `near me` flow resolves the user's city in this order: browser coordinates →
browser-reported city → IP geolocation → `islamabad` fallback. Placeholder values from the
LLM (`"your city"`, `"current city"`, etc.) are filtered out before resolution.

## API

| Method | Path                                  | Auth | Purpose                                  |
| ------ | ------------------------------------- | :--: | ---------------------------------------- |
| GET    | `/`                                   |  —   | Health check                             |
| POST   | `/api/chats`                          | JWT  | Create chat                              |
| GET    | `/api/chats`                          | JWT  | List the caller's chats (RLS-scoped)     |
| GET    | `/api/chats/{chat_id}`                | JWT  | Chat with messages                       |
| PUT    | `/api/chats/{chat_id}/title`          | JWT  | Rename a chat (`?title=...`)             |
| DELETE | `/api/chats/{chat_id}`                | JWT  | Delete chat + messages                   |
| POST   | `/api/chats/{chat_id}/messages`       | JWT  | Send a message, dispatch to a tool       |
| GET    | `/api/chats/{chat_id}/messages`       | JWT  | List messages in a chat                  |
| POST   | `/api/chat`                           | JWT  | Legacy combined chat endpoint            |
| GET    | `/api/convert-video?url=...`          |  —   | Convert animated WEBP from S3 to MP4     |
| GET    | `/api/image-proxy?url=...`            |  —   | Proxy external images past hotlink rules |

Auth is a Supabase JWT in `Authorization: Bearer <token>`. RLS on the Supabase side limits
each user to their own chats — the backend just forwards the token via a per-request client.

### Message request

```json
{
  "message": "Animate the previous image into a 6 second reel",
  "conversation_history": [{ "role": "user", "content": "..." }],
  "image_base64": "iVBORw0KGgoA...",       // optional, for I2V uploads
  "quality_mode": "balanced",              // "speed" | "balanced" | "quality"
  "current_city": "Lahore",                // for billboard "near me"
  "current_lat": 31.5497,
  "current_lon": 74.3436
}
```

### Message response

```json
{
  "message": "Here's your generated video!",
  "image": "https://<bucket>.s3.amazonaws.com/...",   // or base64 data URL
  "html": null,                                       // populated for website_generation
  "tool": "video_generation",
  "chat_id": "uuid",
  "conversation_history": [ ... ]
}
```

## Configuration

```env
# Required
HF_TOKEN=hf_xxx

# Server
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Supabase (chat persistence + auth)
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOi...

# AWS S3 (generated image / video storage)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
S3_BUCKET_NAME=

# Model device placement (cuda | cpu)
MODEL_LLM_DEVICE=cuda
MODEL_IMAGE_DEVICE=cuda
MODEL_TEXT_DEVICE=cuda
MODEL_WEBSITE_DEVICE=cpu        # website gen is HTTP-only; device is unused

# Remote video backend (HF Inference Providers)
VIDEO_BACKEND_TOKEN=
VIDEO_BACKEND_PROVIDER=
VIDEO_BACKEND_T2V_MODEL=
VIDEO_BACKEND_I2V_MODEL=
VIDEO_BACKEND_TIMEOUT=600

# Local video fallback (ComfyUI)
COMFYUI_URL=http://127.0.0.1:8188
```

**Device placement on a single GPU.** If you only have one 8 GB card, put LLM and Image on
`cuda` and Text on `cpu` — the orchestrator stays warm in VRAM, the image model loads when
needed, and text generation falls back to CPU (slower but doesn't fight for VRAM). With 16
GB+, set everything to `cuda`.

**Falling back gracefully.** Without Supabase, the API will refuse JWT-protected endpoints
— so Supabase is effectively required. Without S3, generated images are returned as
base64 data URLs. Without `VIDEO_BACKEND_*`, video falls back to a local ComfyUI server at
`COMFYUI_URL`.

## Project layout

```
backend/
├── main.py                 FastAPI app, endpoint handlers, message dispatch
├── llm_orchestrator.py     Llama wrapper, tool definitions, tool-call parsing
├── model_loader.py         Lazy load + offload (per-model lock, VRAM swap)
├── config.py               Video backend + ComfyUI workflow constants
├── database_models.py      Pydantic schemas for chats / messages
├── generators/
│   ├── image_generator.py    OpenJourney via diffusers
│   ├── text_generator.py     Qwen2.5 + PEFT/LoRA adapter
│   ├── video_generator.py    HF Inference + ComfyUI fallback
│   └── website_generator.py  DeepSeek-V3 via HF Inference router
├── services/
│   ├── auth.py               Supabase JWT verification (FastAPI dependency)
│   ├── database_service.py   Chat/message CRUD against Supabase
│   ├── storage_service.py    S3 upload + base64 fallback
│   ├── supabase_client.py    Per-user Supabase client factory
│   ├── s3_client.py          boto3 init
│   └── billboard_scraper.py  adbuq.com scrape + geolocation helpers
├── workflows/              ComfyUI JSON graphs (wan2.1_t2v, wan2.1_i2b_fun_1.4b)
├── scripts/                Fine-tuning + dataset scripts (not loaded at runtime)
├── requirements.txt
└── .env.example
```

## Development

```bash
# Auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Sanity check tool dispatch
curl -X POST http://localhost:8000/api/chats/<chat_id>/messages \
  -H "Authorization: Bearer <supabase_jwt>" \
  -H "Content-Type: application/json" \
  -d '{"message": "create a poster for my summer lawn collection"}'
```

For production, run behind Gunicorn:

```bash
pip install gunicorn
gunicorn main:app -k uvicorn.workers.UvicornWorker -w 1 --bind 0.0.0.0:8000
```

Use `-w 1`, not more — each worker reloads the whole model stack into memory.

## Troubleshooting

- **"Models are still loading"** — Llama 3.2 takes ~30s to load on first start. Subsequent
  requests are instant.
- **`HF_TOKEN` errors** — accept the licence on the Llama and Qwen model pages with the
  same HF account whose token you're using.
- **RLS policy errors from Supabase** — the auth dependency requires a valid JWT; the chat
  / message tables also need RLS policies that scope rows to `auth.uid()`.
- **Out-of-memory on a single GPU** — set `MODEL_TEXT_DEVICE=cpu` (text generation slows
  but image + LLM keep their VRAM).
- **Video generation fails immediately** — either set `VIDEO_BACKEND_*` to a working HF
  Inference provider, or run ComfyUI locally at `COMFYUI_URL` with the workflows in
  `workflows/` and the Wan 2.1 checkpoints they expect.
