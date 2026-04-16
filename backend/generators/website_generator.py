"""
Website generator using the DeepSite approach:
- Full HTML generation via DeepSeek-V3 and HF Inference.
"""
import asyncio
import os
import re
from typing import Optional

import requests

CHAT_COMPLETIONS_URL = "https://router.huggingface.co/v1/chat/completions"
MODEL_ID = "deepseek-ai/DeepSeek-V3:fastest"


def _get_hf_token() -> Optional[str]:
    """Read HF token from env (HF_TOKEN). Strips quotes/whitespace."""
    raw = os.environ.get("HF_TOKEN")
    return raw or None


def _strip_markdown_code_fences(text: str) -> str:
    """
    Remove leading/trailing markdown code fences like ```html ... ``` from model output.
    """
    if not text:
        return ""
    s = text.strip()
    s = re.sub(r"^\s*```[a-zA-Z0-9_-]*\s*\n?", "", s)
    s = re.sub(r"\n?\s*```\s*$", "", s).strip()
    return s


def _ensure_doctype(html: str) -> str:
    """Ensure the HTML starts with <!DOCTYPE html>."""
    if not html:
        return ""
    s = html.lstrip()
    if re.match(r"(?is)^\s*<!doctype\s+html", s):
        return s
    return "<!DOCTYPE html>\n" + s


class WebsiteGenerator:
    """
    Generates full HTML landing pages via DeepSeek-V3 and HF Inference.
    """

    def __init__(self, device: Optional[str] = None):
        token = _get_hf_token()
        self._token = token
        self.model_loaded = bool(token)
        self.model = None
        self.tokenizer = None
        if not token:
            print("WebsiteGenerator: No HF_TOKEN set. Set one for Inference.")

    def _build_messages(self, prompt: str) -> list:
        """Build messages for full-page generation (DeepSite-style)."""
        system = (
            "You create landing pages for eastern clothing brands (modest wear, traditional and contemporary South Asian / Middle Eastern fashion, etc.). "
            "ONLY USE HTML, CSS AND JAVASCRIPT. Create the best UI possible using only HTML, CSS and JAVASCRIPT. "
            "Elaborate as much as you can to create something unique. If needed you may use Tailwind CSS (if so, import it in the head). "
            "ALWAYS return a SINGLE HTML file. No markdown, no code fences, no explanation. "
            "Output ONLY the raw HTML document (complete with <!DOCTYPE html>, <html>, <head>, <body>)."
        )
        user = f"""Create a single-file, high-conversion landing page for this eastern clothing brand:
{prompt}

Default context: This is for an eastern clothing brand (e.g. modest wear, kurta/shalwar, abaya, sherwani, fusion wear, eastern textiles). Use aesthetics, tone, and copy that fit this niche (elegant, culturally relevant, premium fabric/craft focus). If the user's prompt specifies a different angle, follow that while keeping the eastern clothing brand focus unless they clearly ask for something else.

Requirements:
- Output ONLY raw HTML (complete document: <!DOCTYPE html>, <html>, <head>, <body>).
- Put all CSS in a <style> tag in <head>. No external stylesheets unless you add Tailwind via CDN in <head>.
- Prefer no JavaScript; use HTML + CSS only (e.g. <details>/<summary> for accordions).
- No local or broken image paths; use inline SVG/CSS or stable public URLs only.
- No triple backticks (```) in the output.
- No placeholder text (Lorem ipsum, "Testimonial 1", etc.); use believable, brand-relevant copy.
- Modern, premium look: cohesive palette, gradients, CSS variables, clear typography, cards, shadows.
- Include: navbar, hero (headline + CTAs + visual block), social proof, features grid, pricing, FAQ (accordion), lead form, footer.
- Semantic HTML5, meta viewport, mobile-first responsive. Nav anchors must match section ids.

Output ONLY the raw HTML document, nothing else."""
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def _call_api(self, messages: list, max_tokens: int = 4000) -> str:
        """Single non-streaming call to HF chat completions. Returns content or empty string."""
        if not self.model_loaded or not self._token:
            return ""
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": MODEL_ID,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        try:
            r = requests.post(
                CHAT_COMPLETIONS_URL,
                json=payload,
                headers=headers,
                timeout=180,
            )
            data = r.json()
            choices = data.get("choices") if isinstance(data, dict) else None
            if not choices or not isinstance(choices[0].get("message"), dict):
                return ""
            return (choices[0]["message"].get("content") or "").strip()
        except requests.exceptions.RequestException as e:
            print(f"WebsiteGenerator error: {e}")
            return ""

    def _generate_sync(self, prompt: str) -> str:
        """Returns full HTML or empty string on error."""
        if not self.model_loaded or not self._token:
            return ""
        messages = self._build_messages(prompt)
        print(f"Website generation started (DeepSite-style, model={MODEL_ID})...")
        raw = self._call_api(messages, max_tokens=4000)
        print("Website generation finished.")
        if not raw:
            return ""
        raw = _strip_markdown_code_fences(raw)
        if raw and "</html>" not in raw.lower():
            raw = raw.rstrip() + "\n</html>"
        return _ensure_doctype(raw)

    async def generate(self, prompt: str) -> str:
        """Generate a full landing-page HTML document (DeepSite-style, DeepSeek-V3)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._generate_sync, prompt)
