# Brandmate

AI-powered brand automation for Eastern clothing brands. An LLM orchestrator routes
natural-language requests to specialized image, text, video, website, and billboard-search
tools — so a single prompt can generate a marketing poster, a landing page, a promo reel,
or surface real outdoor advertising inventory in a Pakistani city.

![Brandmate demo](assets/demo.gif)

## What it does

| Capability             | Powered by                                      |
| ---------------------- | ----------------------------------------------- |
| LLM orchestration      | Llama 3.2 3B Instruct (local, tool calling)     |
| Image generation       | OpenJourney (Stable Diffusion v1.5, local)      |
| Text generation        | Qwen2.5-1.5B-Instruct + LoRA fine-tune (local)  |
| Video generation       | Wan 2.1 via ComfyUI (local) / HF Inference (remote) |
| Website generation     | DeepSeek-V3 via Hugging Face Inference          |
| Billboard / OOH search | Scraper for adbuq.com (Pakistani cities)        |

Conversations, messages, and uploaded references persist in Supabase. Generated images and
videos land in AWS S3 (with base64 as a fallback when S3 isn't configured).

## Architecture

```
                ┌──────────────────────────┐
                │   React frontend (Vite)  │
                │   Supabase auth + RLS    │
                └────────────┬─────────────┘
                             │  HTTPS + Bearer JWT
                ┌────────────▼─────────────┐
                │   FastAPI backend        │
                │   LLM orchestrator       │
                └─┬──────────┬──────┬──────┘
                  │          │      │
        ┌─────────▼──┐  ┌────▼───┐  ▼────────────────────────┐
        │ Image / Text│  │ Video │  │ Website / Billboards   │
        │ (lazy load, │  │ (Wan  │  │ (DeepSeek-V3 HTTP /    │
        │  swap VRAM) │  │  2.1) │  │  adbuq scraper)        │
        └─────────────┘  └───────┘  └────────────────────────┘
```

The LLM stays loaded for the life of the server. Image and text models load on demand and
offload between calls — they swap VRAM so a single 8 GB GPU can host all three.

## Quick start

```bash
git clone <repository-url> brandmate
cd brandmate
```

Backend:

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env          # fill in HF_TOKEN at minimum
python main.py                # http://localhost:8000
```

Frontend:

```bash
cd frontend
cp .env.example .env          # fill in Supabase credentials
npm install
npm run dev                   # http://localhost:5173
```

Or on Windows, run `start_dev.bat` from the repo root.

Per-subsystem details live in [`backend/README.md`](backend/README.md) and
[`frontend/README.md`](frontend/README.md).

## Requirements

- Node.js 18+
- Python 3.10+
- 16 GB RAM (8 GB minimum, slow)
- NVIDIA GPU with 8 GB+ VRAM recommended; CPU-only works but is much slower
- ~15 GB free disk space for model weights
- Hugging Face token (required — Llama and Qwen are gated)
- Optional: Supabase project, AWS S3 bucket, ComfyUI install (for local video)

## Repository layout

```
brandmate/
├── frontend/               React 19 + Vite + Tailwind + ShadCN
├── backend/                FastAPI + transformers/diffusers
│   ├── main.py             API surface
│   ├── llm_orchestrator.py Llama-based tool router
│   ├── model_loader.py     Lazy load + offload (VRAM swap)
│   ├── generators/         image, text, video, website
│   ├── services/           database, storage, auth, billboard scraper
│   ├── workflows/          ComfyUI graphs for Wan 2.1 (T2V + I2V)
│   └── scripts/            fine-tuning + dataset utilities
├── assets/                 demo gif
└── start_dev.bat           dev launcher (Windows)
```

## License

Final Year Project, FAST NUCES Islamabad.

## Acknowledgments

Meta (Llama 3.2), Alibaba (Qwen2.5, Wan 2.1), DeepSeek, PromptHero (OpenJourney),
Hugging Face, Supabase, ShadCN, and the FastAPI / React communities.
