import asyncio
import os
import re
from typing import Optional

import requests

CHAT_COMPLETIONS_URL = "https://router.huggingface.co/v1/chat/completions"
API_MODEL_ID = "Qwen/Qwen2.5-Coder-7B-Instruct:fastest"

def _get_hf_token() -> Optional[str]:
    """Read HF API token from env (HF_TOKEN). Strips quotes/whitespace."""
    raw = os.environ.get("HF_TOKEN")
    return raw or None


def _strip_markdown_code_fences(text: str) -> str:
    """
    Remove leading/trailing markdown code fences like ```html ... ``` from model output.
    Models often ignore 'no code fences' instructions, so we normalize here.
    """
    if not text:
        return ""
    s = text.strip()
    # Leading fence: ``` or ```html
    s = re.sub(r"^\s*```[a-zA-Z0-9_-]*\s*\n?", "", s)
    # Trailing fence: ``` on last line (optionally preceded by newline)
    s = re.sub(r"\n?\s*```\s*$", "", s).strip()
    return s


def _ensure_doctype(html: str) -> str:
    """Ensure the HTML starts with <!DOCTYPE html> (case-insensitive check)."""
    if not html:
        return ""
    s = html.lstrip()
    if re.match(r"(?is)^\s*<!doctype\s+html", s):
        return s
    return "<!DOCTYPE html>\n" + s


class WebsiteGenerator:
    """Generates full HTML landing pages via HF Inference API (router)."""

    def __init__(self, device: Optional[str] = None):
        token = _get_hf_token()
        self._token = token
        self.model_loaded = bool(token)
        self.model = None
        self.tokenizer = None
        if not token:
            print("WebsiteGenerator: No HF_TOKEN set. Set one for Inference API.")

    def _build_messages(self, prompt: str) -> list:
        """Build system + user messages so the model outputs only HTML."""
        system = (
            "You are an expert product designer and front-end engineer. "
            "Return ONLY a complete, valid, single-file HTML document (no markdown, no code fences, no explanation). "
            "All CSS must be inside exactly one <style> tag in <head>. No external CSS, no Tailwind CDN, no external fonts. "
            "No JavaScript. The page must look modern, premium, and production-ready."
        )
        user = f"""Create a single-file, high-conversion landing page for this brand/product:
{prompt}

Requirements:
- Output ONLY raw HTML (a complete document with <!DOCTYPE html>, <html>, <head>, <body>).
- Put all CSS in exactly one <style> tag inside <head>. No external stylesheets, no inline style attributes unless absolutely necessary.
- No JavaScript. Use only HTML + CSS. You may use <details>/<summary> for accordion behavior.
- Assets/images: do NOT reference local files (e.g. src="assets/...", src="./...", src="C:/...") or unknown/broken URLs. Prefer inline SVG/CSS for visuals. If you use images, only use clearly public, stable URLs you are confident will resolve; otherwise omit the image.
- Absolutely DO NOT include triple backticks (```) anywhere in the output.
- DO NOT use placeholder text like “Lorem ipsum”, “Testimonial 1”, “Customer Name”, “Feature 1”. Write believable, brand-relevant copy.

Design quality (must feel modern):
- Choose a cohesive, modern color palette with strong contrast and excellent readability.
- Use subtle background gradients that enhance depth (e.g. radial/linear mixes), but keep text highly readable.
- Define design tokens via CSS variables (:root) for colors, spacing, radii, shadows, and typography.
- Use generous whitespace, a max-width container, and a clear typographic scale (headline, subhead, body, small).
- Use a modern system font stack (no external font imports). Apply crisp font smoothing.
- Use depth: elevated cards with soft shadows, borders with low opacity, and tasteful background gradients.
- Ensure accessible contrast and visible focus states (keyboard navigation). Avoid tiny text. Include a “skip to content” link.
- Avoid invalid CSS like rgba(var(--some-hex), 0.1). If you need translucency, use rgba() with numeric RGB values or define --accent-rgb: 34, 211, 238 and use rgba(var(--accent-rgb), 0.12).

Components (be specific and polished):
- Navbar: logo/brand name, 3–5 anchor links, and a primary CTA button. Make it sticky or at least visually anchored.
- Hero: bold headline, concise supporting paragraph, 2 CTAs (primary + secondary/ghost), and a right-side visual block built inline (no external images). The visual must feel premium (layered gradients + subtle shapes + optional mock UI card) and be sized responsively; avoid a single huge flat circle or an empty/oversized SVG that dominates the viewport. Add a small trust row (e.g., “Trusted by…”, rating, or 3 micro badges).
- Social proof section: 3 testimonial cards or a metrics strip (e.g., 3 stats). Keep copy relevant (no Lorem ipsum).
- Features: a responsive grid of feature cards (6 items) with small inline icons (simple inline SVG ok) and concise benefit-focused copy.
- Pricing: 3 tier cards with a “Most popular” highlight on the middle tier, clear price, 4–6 bullet features, and a CTA per tier.
- FAQ: accordion using <details>/<summary> with at least 5 questions; style it like a modern UI (chevron indicator, spacing, hover).
- Lead capture: include at least one small form (newsletter or “Request a demo”) with excellent input styling (padding, border, focus ring, placeholder, disabled state). Use label + input (accessible), and a primary submit button.
- Footer: include secondary navigation, social links (text-only), and a short legal line.

Button & field styling (make them feel premium):
- Buttons: consistent height (e.g. 44–48px), radius, hover/active transitions, subtle shadow, and clear disabled styles.
- Primary button: vibrant gradient or solid accent; secondary button: outline/ghost with hover fill; both must have focus-visible rings.
- Inputs: rounded, soft border, background tint, focus ring matching accent, error/valid example styling (can be via helper text classes).

Layout & responsiveness:
- Mobile-first. Use CSS grid/flex with breakpoints so sections stack cleanly on small screens and align in columns on larger screens.
- Use section padding (e.g. 72–96px desktop, 48–64px mobile), consistent gaps, and readable line lengths.
- Structure every section like:
  <section ...><div class="container"> ... section content ... </div></section>
  If a section needs a flex/grid layout, apply the layout to an inner wrapper inside the container (or make the container itself the layout), but do not break the layout by nesting a non-flex container between the flex parent and cards.

HTML structure constraints:
- Use semantic HTML5 (<header>, <main>, <section>, <nav>, <footer>).
- Include <meta charset="utf-8"> and <meta name="viewport" content="width=device-width, initial-scale=1">.
- Anchor links must scroll to real section ids.
- Before finalizing, verify: exactly one <style> tag, no code fences, one <!DOCTYPE html>, no Lorem/placeholder copy, and all nav anchors match real ids.

Output ONLY the raw HTML document, nothing else."""
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def _generate_sync(self, prompt: str) -> str:
        """Returns HTML or empty string on error."""
        if not self.model_loaded or not self._token:
            return ""

        messages = self._build_messages(prompt)
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

        try:
            payload = {
                "model": API_MODEL_ID,
                "messages": messages,
                "max_tokens": 2400,
                "temperature": 0.6,
            }

            print(f"Website generation started (HF Inference API, model={API_MODEL_ID})...")
            r = requests.post(
                CHAT_COMPLETIONS_URL,
                json=payload,
                headers=headers,
                timeout=120,
            )
            print("Website generation finished.")

            data = r.json()
            choices = data.get("choices") if isinstance(data, dict) else None
            if not choices or not isinstance(choices[0].get("message"), dict):
                print(f"Unexpected API response shape: {type(data)}")
                return ""
            raw_html = (choices[0]["message"].get("content") or "").strip()
            raw_html = _strip_markdown_code_fences(raw_html)
            if raw_html and "</html>" not in raw_html.lower():
                raw_html = raw_html.rstrip() + "\n</html>"
            return _ensure_doctype(raw_html)
        except requests.exceptions.RequestException as e:
            print(f"Landing page generation error: {e}")
            return ""

    async def generate(self, prompt: str) -> str:
        """Generate a full landing-page HTML document"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._generate_sync, prompt)
