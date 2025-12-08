"""
Text Generator using Qwen2-1.5B-Instruct
Specializes in generating marketing content for Eastern clothing brands

Performance Notes:
- On CPU: Expect 10-20 seconds for short content (50-100 tokens), 20-40 seconds for longer content
- On GPU: Expect 1-5 seconds for most content types
- Optimizations: Content-type specific token limits, inference mode, KV cache, greedy decoding
- For faster CPU inference, consider using a quantized model or smaller model variant
"""
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from typing import Optional


class TextGenerator:
    def __init__(self):
        model_name = "Qwen/Qwen2-1.5B-Instruct"
        print(f"Loading Qwen2-1.5B-Instruct model: {model_name}")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                low_cpu_mem_usage=True,  # More efficient memory usage
            )
            
            # Optimize model for inference
            self.model.eval()  # Set to evaluation mode
            
            # Try to compile model for faster inference (PyTorch 2.0+)
            try:
                if hasattr(torch, 'compile') and torch.cuda.is_available():
                    self.model = torch.compile(self.model, mode="reduce-overhead")
                    print("Model compiled with torch.compile for faster inference")
            except Exception as compile_error:
                print(f"Could not compile model (this is okay): {compile_error}")
            
            print("Qwen2-1.5B-Instruct loaded successfully!")
            self.model_loaded = True
            
        except Exception as e:
            print(f"Error loading Qwen2-1.5B-Instruct: {e}")
            self.model_loaded = False
            self.tokenizer = None
            self.model = None
    
    def _get_system_prompt(self) -> str:
        """System prompt for marketing content generation"""
        return """You are a marketing assistant for Eastern clothing brands. Generate creative, culturally relevant content. Be concise, persuasive, and professional."""

    def _get_max_tokens_for_content_type(self, content_type: str) -> int:
        """Get appropriate max_tokens based on content type for faster generation"""
        token_limits = {
            "caption": 80,
            "slogan": 50,
            "ad_copy": 60,
            "meta_description": 40,
            "whatsapp_broadcast": 80,
            "description": 120,
            "marketing_copy": 150,
            "email": 200,
            "launch_announcement": 120,
            "sale_promo": 80,
            "campaign_idea": 300,
            "reel_idea": 200,
            "story_content": 150,
            "engagement_post": 100,
            "influencer_brief": 250,
            "category_description": 180,
            "blog_post": 250,
        }
        return token_limits.get(content_type, 150)

    async def generate_content(
        self,
        topic: str,
        content_type: str = "marketing_copy",
        max_tokens: Optional[int] = None,  # Auto-determine if None
        temperature: float = 0.7,
    ) -> str:
        """
        Generate marketing content based on topic and content type
        
        Args:
            topic: The subject matter to write about
            content_type: Type of content (caption, description, marketing_copy, slogan, blog_post)
            max_tokens: Maximum tokens to generate (auto-determined if None)
            temperature: Creativity level (0.0-1.0)
        
        Returns:
            Generated marketing content
        """
        if not self.model_loaded:
            return f"Text generation service is unavailable. Topic: {topic}"
        
        # Auto-determine max_tokens if not provided
        if max_tokens is None:
            max_tokens = self._get_max_tokens_for_content_type(content_type)
        
        try:
            # Create user prompt based on content type
            user_prompt = self._create_user_prompt(topic, content_type)
            
            # Build messages for chat template
            messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": user_prompt}
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
                    max_new_tokens=max_tokens,
                    do_sample=temperature > 0.1,
                    temperature=temperature if temperature > 0.1 else None,
                    top_p=0.9 if temperature > 0.1 else None,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,  # Early stopping
                    num_beams=1,  # Greedy decoding for speed
                    use_cache=True,  # Enable KV cache for faster generation
                    repetition_penalty=1.1  # Prevent repetition without slowing down
                )
            
            # Extract only new tokens
            generated_ids = generated[0][len(inputs["input_ids"][0]):]
            response = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
            
            return response.strip()
            
        except Exception as e:
            print(f"Error generating text content: {e}")
            return f"Error generating content for: {topic}"
    
    def _create_user_prompt(self, topic: str, content_type: str) -> str:
        """Create appropriate user prompt based on content type"""
        
        prompts = {
            # Core Marketing Content
            "caption": f"Instagram caption for: {topic}. Include hook, emojis, CTA, hashtags.",
            "description": f"Product description for: {topic}. Highlight features, benefits, materials. 100-150 words.",
            "marketing_copy": f"Marketing copy for: {topic}. Headline, body, CTA, USPs.",
            "slogan": f"5 catchy slogans for: {topic}. Under 10 words each. Elegant and modern.",
            "ad_copy": f"Ad copy for: {topic}. Headline (30 chars), subheadline (50 chars), description (90 chars), CTA button.",
            "email": f"Marketing email for: {topic}. Subject line, greeting, body (150-200 words), CTA, sign-off.",

            # Campaign & Strategy
            "campaign_idea": f"Marketing campaign for: {topic}. Theme, audience, 3 key messages, 3-5 social posts, email sequence, offers.",
            "launch_announcement": f"Collection launch announcement for: {topic}. Opening, highlights, availability, CTA. 100-150 words.",
            "sale_promo": f"Sale announcement for: {topic}. Headline, discount, urgency, CTA. Under 100 words.",

            # Social Media Specific
            "reel_idea": f"Reel concept for: {topic}. 15-30s, 4-6 scenes, audio style, text overlays, hook, CTA.",
            "story_content": f"5 Instagram story slides for: {topic}. Visual + text per slide, interactive elements, final CTA.",
            "engagement_post": f"Engagement post for: {topic}. Poll/Question/Quiz format, fashion-related question, options, caption.",

            # Business Communication
            "whatsapp_broadcast": f"WhatsApp broadcast for: {topic}. Greeting, highlight, PKR price, ordering info. Under 100 words, emojis.",
            "influencer_brief": f"Influencer brief for: {topic}. Objective, product, 3-4 talking points, content requirements, hashtags, timeline.",

            # SEO & Web Content
            "meta_description": f"SEO meta description for: {topic}. 150-160 chars, keyword, benefit, CTA.",
            "category_description": f"Category page description for: {topic}. SEO intro, features, fabrics, styles. 150-200 words.",

            # Legacy support
            "blog_post": f"Blog post outline for: {topic}. Title, intro (100-150 words), 5 headings, SEO-friendly."
        }
        
        return prompts.get(content_type, f"Marketing copy for: {topic}")
    
    async def generate_campaign_ideas(self, brand_info: str, season: str = "general") -> str:
        """Generate marketing campaign ideas for a brand"""
        if not self.model_loaded:
            return f"Text generation service is unavailable."
        
        user_prompt = f"Marketing campaign for Eastern clothing brand. Brand: {brand_info}. Season: {season}. Include: theme, tagline, audience, 3-5 social posts, email sequence, offers, visual suggestions. Culturally relevant and modern."

        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            
            inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
            
            with torch.inference_mode():
                generated = self.model.generate(
                    **inputs,
                    max_new_tokens=500,
                    do_sample=True,
                    temperature=0.8,
                    top_p=0.9,
                    pad_token_id=self.tokenizer.eos_token_id,
                    num_beams=1,
                    use_cache=True,
                    repetition_penalty=1.1
                )
            
            generated_ids = generated[0][len(inputs["input_ids"][0]):]
            response = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
            
            return response.strip()
            
        except Exception as e:
            print(f"Error generating campaign ideas: {e}")
            return f"Error generating campaign for: {brand_info}"
