"""
Text Generator using Qwen2-1.5B-Instruct
Specializes in generating marketing content for Eastern clothing brands
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
            )
            
            print("Qwen2-1.5B-Instruct loaded successfully!")
            self.model_loaded = True
            
        except Exception as e:
            print(f"Error loading Qwen2-1.5B-Instruct: {e}")
            self.model_loaded = False
            self.tokenizer = None
            self.model = None
    
    def _get_system_prompt(self) -> str:
        """System prompt for marketing content generation"""
        return """You are a professional marketing assistant specializing in fashion, particularly Eastern and traditional clothing.
Your role is to generate creative, persuasive, and culturally relevant marketing content. You can:

1. Write ad copy, slogans, hooks, and call-to-actions for social media, email campaigns, landing pages, and advertisements.
2. Generate social media posts, captions, and short-form content, adapted to the platform (Facebook, Instagram, TikTok, LinkedIn, etc.).
3. Draft blog posts, articles, newsletters, and long-form content for content marketing or SEO purposes.
4. Create marketing campaign ideas, including seasonal, festive, or event-based campaigns, with appropriate themes and messaging.
5. Propose multi-channel strategies combining social media, email, blog, and paid ads.
6. Help maintain brand voice and tone: consistent, culturally relevant, elegant, and modern.
7. Suggest variations and A/B test ideas for ad copy, social media posts, and email sequences.
8. Provide insights on audience targeting, engagement hooks, and creative messaging.
9. Be aware of trends, cultural nuances, and festival seasons when generating marketing ideas.
10. Always produce content that is engaging, persuasive, and suitable for the target audience.

When responding:
- Be creative, professional, and persuasive.
- Respect cultural context and traditions of Eastern clothing.
- Provide multiple variations when possible.
- Keep responses concise but impactful."""

    async def generate_content(
        self,
        topic: str,
        content_type: str = "marketing_copy",
        max_tokens: int = 300,
        temperature: float = 0.7,
    ) -> str:
        """
        Generate marketing content based on topic and content type
        
        Args:
            topic: The subject matter to write about
            content_type: Type of content (caption, description, marketing_copy, slogan, blog_post)
            max_tokens: Maximum tokens to generate
            temperature: Creativity level (0.0-1.0)
        
        Returns:
            Generated marketing content
        """
        if not self.model_loaded:
            return f"Text generation service is unavailable. Topic: {topic}"
        
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
            generated = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=True,
                temperature=temperature,
                top_p=0.9,
                pad_token_id=self.tokenizer.eos_token_id
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
            "caption": f"""Write an engaging Instagram/social media caption for: {topic}

Requirements:
- Catchy opening hook
- Relevant emojis (2-4)
- Call-to-action
- 2-3 relevant hashtags
- Keep it concise (under 150 words)""",

            "description": f"""Write a compelling product description for: {topic}

Requirements:
- Highlight key features and benefits
- Use sensory and emotional language
- Include fabric/material details if relevant
- Make it appealing to the target audience
- 100-150 words""",

            "marketing_copy": f"""Create persuasive marketing copy for: {topic}

Requirements:
- Attention-grabbing headline
- Engaging body copy
- Strong call-to-action
- Highlight unique selling points
- Suitable for ads or promotional materials""",

            "slogan": f"""Create catchy slogans/taglines for: {topic}

Requirements:
- Provide 5 different options
- Keep each under 10 words
- Make them memorable and brandable
- Mix of elegant and modern tones""",

            "ad_copy": f"""Write advertisement copy for: {topic}

Requirements:
- Primary headline (under 30 characters)
- Secondary headline (under 50 characters)
- Description (under 90 characters)
- Call-to-action button text
- Suitable for Facebook/Instagram ads""",

            "email": f"""Write a marketing email for: {topic}

Requirements:
- Catchy subject line
- Personalized greeting
- Compelling body (150-200 words)
- Clear call-to-action
- Professional sign-off""",

            # Campaign & Strategy
            "campaign_idea": f"""Create a complete marketing campaign idea for: {topic}

Requirements:
- Campaign name/theme
- Target audience description
- Key messaging points (3)
- 3 social media post ideas
- Email sequence outline (3 emails)
- Promotional offer suggestion
- 1-2 week timeline""",

            "launch_announcement": f"""Write a collection launch announcement for: {topic}

Requirements:
- Exciting opening line
- What's new in this collection
- Key highlights (fabric, designs, colors)
- Launch availability
- Call-to-action
- 100-150 words""",

            "sale_promo": f"""Write a promotional/sale announcement for: {topic}

Requirements:
- Attention-grabbing headline
- Discount/offer details
- Urgency element (limited time/stock)
- What's included
- Clear call-to-action
- Under 100 words""",

            # Social Media Specific
            "reel_idea": f"""Create a social media reel/short video concept for: {topic}

Requirements:
- Video concept (15-30 seconds)
- Scene-by-scene breakdown (4-6 scenes)
- Suggested audio/music style
- Text overlays for each scene
- Hook in first 3 seconds
- Call-to-action at end""",

            "story_content": f"""Create Instagram/Facebook story content ideas for: {topic}

Requirements:
- 5 story slide ideas in sequence
- Each slide: visual description + text overlay
- Interactive elements (polls, questions, sliders)
- Mix of product showcase and engagement
- Swipe-up/link CTA on final slide""",

            "engagement_post": f"""Create an engagement post for: {topic}

Requirements:
- Choose format: Poll OR Question OR This-or-That OR Quiz
- Engaging question related to fashion/style
- 2-4 answer options if applicable
- Brief caption with context
- Encourage comments/shares""",

            # Business Communication
            "whatsapp_broadcast": f"""Write a WhatsApp business broadcast message for: {topic}

Requirements:
- Friendly greeting
- Brief product/offer highlight
- Price range mention (use PKR)
- How to order (reply/call/visit)
- Under 100 words
- Include 2-3 relevant emojis""",

            "influencer_brief": f"""Create an influencer collaboration brief for: {topic}

Requirements:
- Campaign objective
- Product to feature
- Key talking points (3-4)
- Content requirements (posts, stories, reels)
- Hashtags to use
- Do's and Don'ts
- Deliverables timeline""",

            # SEO & Web Content
            "meta_description": f"""Write an SEO meta description for: {topic}

Requirements:
- 150-160 characters exactly
- Include primary keyword naturally
- Compelling and click-worthy
- Mention key benefit
- Include call-to-action""",

            "category_description": f"""Write a website category page description for: {topic}

Requirements:
- SEO-optimized opening paragraph
- Highlight collection features
- Mention fabric types, styles available
- Appeal to target audience
- 150-200 words
- Include natural keywords""",

            # Legacy support
            "blog_post": f"""Write a blog post outline and introduction for: {topic}

Requirements:
- Compelling title
- Introduction paragraph (100-150 words)
- 5 main section headings
- SEO-friendly approach
- Engaging and informative tone"""
        }
        
        return prompts.get(content_type, prompts["marketing_copy"])
    
    async def generate_campaign_ideas(self, brand_info: str, season: str = "general") -> str:
        """Generate marketing campaign ideas for a brand"""
        if not self.model_loaded:
            return f"Text generation service is unavailable."
        
        user_prompt = f"""Create a comprehensive marketing campaign for an Eastern clothing brand.

Brand Information: {brand_info}
Season/Occasion: {season}

Please provide:
1. Campaign theme and name
2. Key messaging and tagline
3. Target audience description
4. Social media content ideas (3-5 posts)
5. Email marketing sequence outline
6. Promotional offers/hooks
7. Visual content suggestions (for image generation)

Make it culturally relevant, modern, and appealing to urban young adults."""

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
            generated = self.model.generate(
                **inputs,
                max_new_tokens=500,
                do_sample=True,
                temperature=0.8,
                top_p=0.9,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            generated_ids = generated[0][len(inputs["input_ids"][0]):]
            response = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
            
            return response.strip()
            
        except Exception as e:
            print(f"Error generating campaign ideas: {e}")
            return f"Error generating campaign for: {brand_info}"
