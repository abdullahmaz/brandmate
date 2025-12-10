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
import os
from pathlib import Path
from typing import Optional


class TextGenerator:
    def __init__(self):
        base_model_name = "Qwen/Qwen2.5-0.5B-Instruct"
        
        print(f"Loading Fine Tuned Qwen2.5-0.5B-Instruct model")
        print(f"Base model: {base_model_name}")
        
        try:
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Load base model
            self.model = AutoModelForCausalLM.from_pretrained(
                base_model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                low_cpu_mem_usage=True,
                trust_remote_code=True
            )
            
            print("✓ Model loaded successfully!")
            
            # Optimize model for inference
            self.model.eval()  # Set to evaluation mode
            
            # Try to compile model for faster inference (PyTorch 2.0+)
            try:
                if hasattr(torch, 'compile') and torch.cuda.is_available():
                    self.model = torch.compile(self.model, mode="reduce-overhead")
                    print("Model compiled with torch.compile for faster inference")
            except Exception as compile_error:
                print(f"Could not compile model (this is okay): {compile_error}")
            
            self.model_loaded = True
            
        except Exception as e:
            print(f"Error loading model: {e}")
            self.model_loaded = False
            self.tokenizer = None
            self.model = None
    
    def _get_system_prompt(self) -> str:
        """System prompt for marketing content generation"""
        return """You are an expert marketing copywriter for Pakistani and Eastern fashion brands.

Your job: Turn the user's prompt into clear and compelling content for fashion brands—such as social captions, proposals, emails, website copy, or campaign ideas.

Focus:
- Write for modern Pakistani/Eastern brands and audiences
- Feature clothing suited for summer and winter collections
- Include cultural and festive context (Eid, weddings, seasons) where relevant

Style:
- Use elegant, sophisticated language tailored to Pakistani culture
- Use relevant emojis and hashtags for social content (e.g. #PakistaniFashion)
- Keep a polished, professional tone for formal business content (no emojis)
- Organize longer pieces with proper headings and bullet points

Instructions:
- Follow the user's requirements closely; let the brief decide content type, length, and detail
- Use Pakistani English and PKR for prices when mentioned
- Avoid repeating ideas; keep writing specific and concise"""


    async def generate_content(
        self,
        prompt: str,
        temperature: float = 0.7,
    ) -> str:
        """
        Generate marketing content based on topic and content type
        
        Args:
            topic: The subject matter, detailed prompt, or creative brief to write about
                   Can be a simple topic or a detailed creative prompt with specific requirements
            content_type: Type of content (optional, for context only - topic can include full instructions)
            temperature: Creativity level (0.0-1.0)
        
        Returns:
            Generated marketing content
        """
        if not self.model_loaded:
            return f"Text generation service is unavailable"
        
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
