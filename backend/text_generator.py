"""
Text Generator using Fine-tuned Qwen2.5-0.5B-Instruct with LoRA
Specializes in generating marketing content for Eastern clothing brands

Performance Notes:
- On CPU: Expect 10-20 seconds for short content (50-100 tokens), 20-40 seconds for longer content
- On GPU: Expect 1-5 seconds for most content types
- Optimizations: Content-type specific token limits, inference mode, KV cache, greedy decoding
- For faster CPU inference, consider using a quantized model or smaller model variant
"""
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch
import gc  # For memory cleanup when unloading models
import os
from pathlib import Path
from typing import Optional


class TextGenerator:
    def __init__(self):
        """Initialize TextGenerator with lazy loading - model loads only when needed"""
        self.base_model_name = "Qwen/Qwen2-1.5B-Instruct"
        self.model = None
        self.tokenizer = None
        self.model_loaded = False
        
        print("TextGenerator initialized with lazy loading (model will load on first use)")
    
    def load_model(self):
        """Load model into VRAM when needed - called before generation"""
        if self.model_loaded:
            print("Text model already loaded, skipping...")
            return
        
        print(f"Loading Fine Tuned Qwen2.5-0.5B-Instruct model into VRAM...")
        print(f"Base model: {self.base_model_name}")
        
        try:
            # Load tokenizer (lightweight, stays in memory)
            if self.tokenizer is None:
                self.tokenizer = AutoTokenizer.from_pretrained(self.base_model_name, trust_remote_code=True)
                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Load base model to VRAM
            self.model = AutoModelForCausalLM.from_pretrained(
                self.base_model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                low_cpu_mem_usage=True,
                trust_remote_code=True
            )
            
            print("[OK] Text model loaded successfully into VRAM!")
            
            # Optimize model for inference
            self.model.eval()  # Set to evaluation mode
            
            # Try to compile model for faster inference (PyTorch 2.0+)
            try:
                if hasattr(torch, 'compile') and torch.cuda.is_available():
                    self.model = torch.compile(self.model, mode="reduce-overhead")
                    print("Text model compiled with torch.compile for faster inference")
            except Exception as compile_error:
                print(f"Could not compile model (this is okay): {compile_error}")
            
            self.model_loaded = True
            
        except Exception as e:
            print(f"Error loading text model: {e}")
            self.model_loaded = False
            self.model = None
    
    def unload_model(self):
        """Unload model from VRAM after generation - frees up memory"""
        if not self.model_loaded or self.model is None:
            print("Text model not loaded, nothing to unload")
            return
        
        print("Unloading text model from VRAM...")
        
        try:
            # Delete model and free VRAM
            del self.model
            self.model = None
            self.model_loaded = False
            
            # Force garbage collection and clear CUDA cache
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            
            print("[OK] Text model unloaded successfully, VRAM freed")
            
        except Exception as e:
            print(f"Error unloading text model: {e}")
            # Still mark as unloaded to prevent issues
            self.model = None
            self.model_loaded = False
    
    def _get_system_prompt(self) -> str:
        """System prompt for marketing content generation"""
        return """You are an expert marketing copywriter for Pakistani and Eastern fashion brands.

    Your job: Turn the user's prompt into clear, compelling, and publication-ready content for fashion brands—such as social captions, campaign ideas, email copy, product descriptions, or proposals.

    Formatting & Styling Rules (apply where appropriate):
    - Headings: Use bold headings for sections using double asterisks. Example: **Collection Overview**
    - Subheadings: Use bold subheadings or short italic lines to separate sections.
    - Paragraphs: Keep paragraphs short (1-3 sentences) for readability.
    - Bullet points: Use concise bullet lists for features, benefits, or steps. Use `-` to create bullets.
    - Emphasis: Use bold for important phrases, and avoid excessive emphasis.
    - Emojis: For social captions, add 1–3 relevant emojis to increase engagement (e.g., 🌙 for Eid, 💃 for weddings, ☀️ for summer). Do NOT use emojis in formal business copy.
    - Hashtags: Include 2–4 relevant hashtags for social posts (e.g., #PakistaniFashion, #EidStyle). Place hashtags at the end or within the caption naturally.

    Voice & Tone:
    - Use elegant, culturally-aware language tailored to Pakistani and Eastern audiences.
    - For formal/business content (proposals, emails, product pages) use a polished professional tone — no emojis, minimal hashtags.
    - For social content (captions, short posts) be friendly, concise, and engaging — include emojis and a clear CTA when relevant.

    Content Structure Guidance:
    - Social caption: Short hook, 1–2 benefit-driven lines, optional emoji, CTA, hashtags. (Length: 50–220 characters)
    - Product description: **Short intro** (1 line), **Key features** (bulleted), **Fit & fabric** (1–2 lines), **Price** (use PKR), **CTA**.
    - Email / Proposal: Use bold section headings, short paragraphs, bullet points for benefits, and a clear CTA.

    Examples (apply the appropriate style):
    - Social caption (festive): **Embrace Eid elegance** ✨ Celebrate in embroidered silks perfect for family gatherings. Shop the Eid edit now 👗💫 #EidStyle #PakistaniFashion
    - Product blurb: **Linen Summer Kurta**
    - Fabric: Lightweight breathable linen
    - Fit: Relaxed, true to size
    - Price: PKR 6,500
    - CTA: Shop now — limited stock

    Practical Rules:
    - Use Pakistani English spelling and formats (e.g., "favour" vs "favor" only if user indicates — otherwise follow the project's default). Use PKR for prices and round sensibly.
    - Avoid repeating ideas, keep content specific and actionable.
    - If the user requests a caption, always include at least one emoji suggestion and 1–3 hashtag suggestions.
    - If the user requests formal copy, do not include emojis or hashtags and keep language strictly professional.

    When in doubt, follow the user's brief exactly and ask clarifying questions if the brief is ambiguous."
"""

    async def generate_content(
        self,
        prompt: str,
        temperature: float = 0.7,
    ) -> str:
        """
        Generate marketing content based on topic and content type
        NOTE: This method now handles automatic model loading and unloading
        
        Args:
            prompt: The subject matter, detailed prompt, or creative brief to write about
            temperature: Creativity level (0.0-1.0)
        
        Returns:
            Generated marketing content
        """
        # Load model before generation (if not already loaded)
        self.load_model()
        
        if not self.model_loaded:
            return f"Text generation service is unavailable - model failed to load"
        
        try:
            # Build messages for chat template
            messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ]
            
            # Apply chat template
            text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            
            # Tokenize and generate
            inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
            
            # Use inference mode for faster CPU/GPU inference
            with torch.inference_mode():
                generated = self.model.generate(
                    **inputs,
                    max_new_tokens=4096,
                    do_sample=temperature > 0.1,
                    temperature=temperature if temperature > 0.1 else None,
                    top_p=0.9 if temperature > 0.1 else None,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    num_beams=1,
                    use_cache=True,
                    repetition_penalty=1.0
                )
            
            generated_ids = generated[0][len(inputs["input_ids"][0]):]
            response = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
            
            return response.strip()
            
        except Exception as e:
            print(f"Error generating text content: {e}")
            return f"Error generating content for: {prompt}"
        finally:
            # Always unload model after generation to free VRAM for other tasks
            self.unload_model()
