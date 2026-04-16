"""
Generate Synthetic Training Data for Qwen2 Fine-tuning - Version 2
Improved with:
- Varied openings and instructions (no repetitive patterns)
- Separate files for each content category
- Appropriate lengths for each content type
- Better stopping criteria and progressive saving
"""

import os
import json
import time
import random
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

try:
    import google.generativeai as genai
except ImportError:
    print("Please install: pip install google-generativeai")
    exit(1)

# ============== CONFIGURATION ==============
API_KEYS = [
    "AIzaSyAn83lePhEGhdyCvOpEG4ixwpZDpI_Qf7E",
    "AIzaSyDpmxWD51tnqVY6tiL7t6AtpefQ7VxDHdg",
    "AIzaSyAYwB8PJXHDwF0SfviHDVceelJFW-3A0HA",
    "AIzaSyBNDOWJWmBw2ZGi8JKVUKlIjraDCUCUDUI",
    "AIzaSyDiHnVc8BuiaHY5fn3jSsP_cpNnjaHiZQM",
]

OUTPUT_DIR = Path("training_data_v2")

# Examples per content type - adjusted for appropriate coverage
EXAMPLES_CONFIG = {
    "social_media": 40,      # captions, engagement posts
    "product_content": 35,   # descriptions, meta, category
    "advertising": 40,       # ad copy, sale promos
    "video_creative": 30,    # reels, stories
    "campaigns": 25,         # campaign ideas, launches (longer content, fewer needed)
    "email_marketing": 30,   # emails, whatsapp
    "brand_strategy": 35,    # slogans, briefs, marketing copy
}

WAIT_TIME_SECONDS = 1.5  # Slightly longer to avoid rate limits

# ============== CLOTHING & CONTEXT ==============

SUMMER_MEN_CLOTHING = [
    "cotton shalwar kameez", "lawn kurta", "summer kurta", "cotton kurta",
    "lawn shalwar kameez", "casual kurta", "mandarin collar kurta",
    "embroidered cotton kurta", "printed lawn kurta", "formal cotton suit"
]

SUMMER_WOMEN_CLOTHING = [
    "lawn suit", "printed lawn suit", "cotton lawn three-piece", "chiffon dupatta set",
    "floral lawn suit", "summer three-piece", "digital print lawn", "embroidered lawn suit",
    "casual kurti", "summer kurti", "cotton kurti", "printed kurti"
]

WINTER_MEN_CLOTHING = [
    "wool waistcoat", "khaddar shalwar kameez", "formal sherwani", "embroidered waistcoat",
    "winter kurta", "khaddar kurta", "velvet waistcoat", "formal wool suit",
    "embroidered khaddar kurta", "winter shalwar kameez"
]

WINTER_WOMEN_CLOTHING = [
    "khaddar suit", "embroidered khaddar suit", "winter shawl", "pashmina shawl",
    "wool shawl", "winter three-piece", "velvet suit", "embroidered winter suit",
    "khaddar kurti", "winter kurti with shawl"
]

ALL_CLOTHING = SUMMER_MEN_CLOTHING + SUMMER_WOMEN_CLOTHING + WINTER_MEN_CLOTHING + WINTER_WOMEN_CLOTHING

BRANDS_STYLE = ["luxury", "affordable", "premium", "boutique", "designer",
                "contemporary", "traditional", "modern fusion", "classic", "trendy"]

SEASONS = ["summer season", "summer collection", "winter season", "winter collection"]

CONTEXTS = ["casual wear", "office wear", "formal occasions", "daily wear",
            "everyday elegance", "weekend outings", "professional settings"]

PLATFORMS = ["Instagram", "Facebook", "TikTok", "website", "email newsletter",
             "WhatsApp status", "Pinterest"]

# ============== VARIED INSTRUCTION TEMPLATES ==============
# Multiple ways to phrase the same request - prevents repetitive training

CAPTION_INSTRUCTIONS = [
    "Write an engaging social media caption for a {style} {clothing} from our {season} for {context}.",
    "Create a captivating Instagram post for a {style} {clothing} ({season}) suitable for {context}.",
    "Craft a scroll-stopping social media caption featuring our {style} {clothing} from the {season}, perfect for {context}.",
    "Generate an attention-grabbing caption for a {style} {clothing} from our {season} collection, ideal for {context}.",
    "Write a compelling social post showcasing our {style} {clothing} ({season}) designed for {context}.",
    "Create viral-worthy caption copy for a {style} {clothing} from our {season}, targeting {context}.",
    "Draft an engaging post about our {style} {clothing} from the {season} for {context} occasions.",
]

ENGAGEMENT_INSTRUCTIONS = [
    "Create an interactive engagement post (poll/quiz) about {style} {clothing} from our {season}.",
    "Write a question-based post to boost engagement for our {style} {clothing} ({season}).",
    "Design a this-or-that style post featuring {style} {clothing} from our {season} collection.",
    "Create a poll post asking followers about their {style} {clothing} preferences for {season}.",
    "Write an engagement-focused caption with a question about {style} {clothing} styling for {context}.",
]

DESCRIPTION_INSTRUCTIONS = [
    "Write a product description for a {style} {clothing} from our {season}.",
    "Create compelling product copy for a {style} {clothing} ({season}) for {context}.",
    "Craft a detailed product description highlighting our {style} {clothing} from the {season}.",
    "Write enticing product details for a {style} {clothing} suited for {context} ({season}).",
    "Generate a persuasive product description for our {style} {clothing} from the {season} collection.",
]

AD_COPY_INSTRUCTIONS = [
    "Write Facebook/Instagram ad copy for a {style} {clothing} from our {season}.",
    "Create a high-converting ad for our {style} {clothing} ({season}) targeting {context}.",
    "Write short advertisement copy for a {style} {clothing} from our {season} collection.",
    "Craft compelling paid ad copy for a {style} {clothing} perfect for {context} ({season}).",
    "Generate click-worthy ad text for our {style} {clothing} from the {season}.",
]

SALE_PROMO_INSTRUCTIONS = [
    "Write a sale announcement for {style} {clothing} from our {season} collection.",
    "Create an urgent promotional post for discounted {style} {clothing} ({season}).",
    "Craft a flash sale announcement for our {style} {clothing} from the {season}.",
    "Write a limited-time offer post for {style} {clothing} suited for {context}.",
    "Generate an exciting discount announcement for our {style} {clothing} ({season}).",
]

REEL_INSTRUCTIONS = [
    "Create a social media reel concept for {style} {clothing} from our {season}.",
    "Design a TikTok/Reels video idea showcasing our {style} {clothing} ({season}).",
    "Write a short-form video script for a {style} {clothing} from our {season} collection.",
    "Create a trending reel concept featuring {style} {clothing} for {context}.",
    "Design an engaging video concept for our {style} {clothing} ({season}).",
]

STORY_INSTRUCTIONS = [
    "Create Instagram story content ideas for {style} {clothing} from our {season}.",
    "Design a 5-slide story sequence featuring our {style} {clothing} ({season}).",
    "Write interactive story content for a {style} {clothing} collection ({season}).",
    "Create engaging story slides showcasing {style} {clothing} for {context}.",
]

CAMPAIGN_INSTRUCTIONS = [
    "Create a complete marketing campaign for {style} {clothing} from our {season}.",
    "Design a comprehensive campaign strategy for our {style} {clothing} ({season}).",
    "Develop a multi-channel marketing campaign for {style} {clothing} targeting {context}.",
    "Create a full campaign proposal for our {style} {clothing} from the {season} collection.",
]

LAUNCH_INSTRUCTIONS = [
    "Write a collection launch announcement for {style} {clothing} ({season}).",
    "Create an exciting new arrival post for our {style} {clothing} from the {season}.",
    "Craft a launch campaign message for {style} {clothing} collection ({season}).",
    "Write a new collection reveal post for our {style} {clothing} ({season}).",
]

EMAIL_INSTRUCTIONS = [
    "Write a marketing email for {style} {clothing} from our {season}.",
    "Create an email campaign for our {style} {clothing} ({season}) targeting {context}.",
    "Draft a promotional email featuring {style} {clothing} from our {season} collection.",
    "Write a newsletter email showcasing our {style} {clothing} ({season}).",
]

WHATSAPP_INSTRUCTIONS = [
    "Write a WhatsApp broadcast message for {style} {clothing} from our {season}.",
    "Create a WhatsApp business message for our {style} {clothing} ({season}).",
    "Draft a catalog share message for {style} {clothing} collection ({season}).",
]

SLOGAN_INSTRUCTIONS = [
    "Create 5 catchy slogans for {style} {clothing} brand ({season}).",
    "Generate memorable taglines for our {style} {clothing} collection ({season}).",
    "Write 5 brand slogans for {style} {clothing} targeting {context}.",
    "Create punchy taglines for our {style} {clothing} ({season}) brand.",
]

INFLUENCER_INSTRUCTIONS = [
    "Create an influencer collaboration brief for {style} {clothing} ({season}).",
    "Write a detailed influencer brief for promoting our {style} {clothing} collection.",
    "Design an influencer campaign brief for {style} {clothing} targeting {context}.",
]

MARKETING_COPY_INSTRUCTIONS = [
    "Write marketing copy for {style} {clothing} from our {season}.",
    "Create persuasive marketing content for our {style} {clothing} ({season}).",
    "Craft brand marketing copy for {style} {clothing} suited for {context}.",
    "Write promotional marketing text for our {style} {clothing} collection ({season}).",
]

META_DESC_INSTRUCTIONS = [
    "Write an SEO meta description for {style} {clothing} product page.",
    "Create a search-optimized meta description for our {style} {clothing}.",
    "Write a click-worthy meta description for {style} {clothing} ({season}).",
]

CATEGORY_DESC_INSTRUCTIONS = [
    "Write a website category description for {style} {clothing} collection ({season}).",
    "Create SEO-friendly category page content for our {style} {clothing}.",
    "Write a collection overview for {style} {clothing} suited for {context}.",
]

# ============== VARIED OPENING STYLES ==============
# To be included in prompts to ensure unique outputs

OPENING_STYLES = [
    "Start with a bold statement",
    "Open with an intriguing question",
    "Begin with an emoji hook",
    "Start with a relatable scenario",
    "Open with a seasonal reference",
    "Begin with a benefit-focused statement",
    "Start with a trendy/modern hook",
    "Open with a cultural reference",
    "Begin with a sensory description",
    "Start with an exclusive/urgency angle",
    "Open with a style tip",
    "Begin with a comfort-focused hook",
]

TONES = [
    "playful and fun",
    "elegant and sophisticated",
    "warm and inviting",
    "trendy and modern",
    "luxurious and premium",
    "friendly and approachable",
    "confident and empowering",
    "cozy and comfortable",
]

# ============== CONTENT TYPE DEFINITIONS ==============

CONTENT_TYPES = {
    "social_media": {
        "file": "social_media_captions.jsonl",
        "types": [
            {"name": "caption", "instructions": CAPTION_INSTRUCTIONS, "length": "50-150 words", "weight": 3},
            {"name": "engagement_post", "instructions": ENGAGEMENT_INSTRUCTIONS, "length": "30-100 words", "weight": 1},
        ]
    },
    "product_content": {
        "file": "product_content.jsonl",
        "types": [
            {"name": "description", "instructions": DESCRIPTION_INSTRUCTIONS, "length": "100-200 words", "weight": 2},
            {"name": "meta_description", "instructions": META_DESC_INSTRUCTIONS, "length": "150-160 characters exactly", "weight": 1},
            {"name": "category_description", "instructions": CATEGORY_DESC_INSTRUCTIONS, "length": "150-200 words", "weight": 1},
        ]
    },
    "advertising": {
        "file": "advertising.jsonl",
        "types": [
            {"name": "ad_copy", "instructions": AD_COPY_INSTRUCTIONS, "length": "30-80 words with headline, description, CTA", "weight": 2},
            {"name": "sale_promo", "instructions": SALE_PROMO_INSTRUCTIONS, "length": "50-100 words", "weight": 1},
        ]
    },
    "video_creative": {
        "file": "video_creative.jsonl",
        "types": [
            {"name": "reel_idea", "instructions": REEL_INSTRUCTIONS, "length": "150-300 words with scene breakdown", "weight": 2},
            {"name": "story_content", "instructions": STORY_INSTRUCTIONS, "length": "150-250 words for 5 slides", "weight": 1},
        ]
    },
    "campaigns": {
        "file": "campaigns.jsonl",
        "types": [
            {"name": "campaign_idea", "instructions": CAMPAIGN_INSTRUCTIONS, "length": "300-500 words with full strategy", "weight": 2},
            {"name": "launch_announcement", "instructions": LAUNCH_INSTRUCTIONS, "length": "100-200 words", "weight": 1},
        ]
    },
    "email_marketing": {
        "file": "email_marketing.jsonl",
        "types": [
            {"name": "email", "instructions": EMAIL_INSTRUCTIONS, "length": "150-250 words with subject line", "weight": 2},
            {"name": "whatsapp_broadcast", "instructions": WHATSAPP_INSTRUCTIONS, "length": "50-100 words", "weight": 1},
        ]
    },
    "brand_strategy": {
        "file": "brand_strategy.jsonl",
        "types": [
            {"name": "slogan", "instructions": SLOGAN_INSTRUCTIONS, "length": "5 slogans, each under 10 words", "weight": 1},
            {"name": "influencer_brief", "instructions": INFLUENCER_INSTRUCTIONS, "length": "200-400 words", "weight": 1},
            {"name": "marketing_copy", "instructions": MARKETING_COPY_INSTRUCTIONS, "length": "100-200 words", "weight": 2},
        ]
    },
}


# ============== PROMPT GENERATION ==============

def get_generation_prompt(content_type: str, instruction: str, clothing: str, season: str, 
                          style: str, context: str, length: str) -> str:
    """Generate a prompt for Gemini with varied opening styles"""
    
    opening_style = random.choice(OPENING_STYLES)
    tone = random.choice(TONES)
    
    base_prompts = {
        "caption": f"""You are a creative marketing expert for Pakistani/Eastern clothing brands.

Task: {instruction}

Product: {style} {clothing}
Season: {season}
Context: {context}

CRITICAL REQUIREMENTS:
1. {opening_style} - DO NOT start with "Beat the heat" or any cliché opener
2. Tone should be {tone}
3. Length: {length}
4. Include 2-4 relevant emojis naturally placed
5. End with a call-to-action
6. Add 2-3 relevant hashtags at the end
7. Culturally appropriate for Pakistani audience
8. Make it unique and fresh - avoid generic phrases

Just write the caption, nothing else.""",

        "engagement_post": f"""You are a creative social media expert for Pakistani/Eastern clothing brands.

Task: {instruction}

Product: {style} {clothing}
Season: {season}

REQUIREMENTS:
1. Create an interactive post (poll, question, this-or-that, or quiz)
2. {opening_style}
3. Tone: {tone}
4. Length: {length}
5. Make it fun and encourage comments
6. Include 1-2 emojis
7. Relevant to Pakistani fashion audience

Just write the engagement post, nothing else.""",

        "description": f"""You are a luxury fashion copywriter for Pakistani/Eastern clothing brands.

Task: {instruction}

Product: {style} {clothing}
Season: {season}
Context: {context}

REQUIREMENTS:
1. {opening_style} - create a unique, compelling opening
2. Tone: {tone}
3. Length: {length}
4. Highlight fabric quality, craftsmanship, design details
5. Use sensory language (feel, touch, drape)
6. Appeal to Pakistani women aged 20-45
7. NO generic openings like "Introducing" or "Discover"

Just write the product description, nothing else.""",

        "meta_description": f"""You are an SEO expert for Pakistani fashion e-commerce.

Task: {instruction}

Product: {style} {clothing}
Season: {season}

REQUIREMENTS:
1. EXACTLY 150-160 characters (count carefully!)
2. Include primary keyword naturally
3. Compelling and click-worthy
4. Include a benefit or unique selling point
5. End with subtle CTA

Just write the meta description, nothing else.""",

        "category_description": f"""You are a fashion content writer for Pakistani clothing brands.

Task: {instruction}

Collection: {style} {clothing}
Season: {season}
Context: {context}

REQUIREMENTS:
1. {opening_style}
2. Length: {length}
3. SEO-friendly with natural keywords
4. Describe the collection's essence
5. Mention fabric types, styles available
6. Appeal to target audience
7. Tone: {tone}

Just write the category description, nothing else.""",

        "ad_copy": f"""You are a performance marketing expert for Pakistani fashion brands.

Task: {instruction}

Product: {style} {clothing}
Season: {season}
Context: {context}

REQUIREMENTS:
1. Format EXACTLY as:
   Headline: [under 30 characters]
   Subheadline: [under 50 characters]
   Description: [under 90 characters]
   CTA: [button text]
2. {opening_style} for headline
3. Focus on benefit/emotion
4. Create urgency without being pushy

Just write the ad copy in the format above, nothing else.""",

        "sale_promo": f"""You are a promotional copywriter for Pakistani fashion brands.

Task: {instruction}

Product: {style} {clothing}
Season: {season}

REQUIREMENTS:
1. {opening_style} - attention-grabbing opener
2. Tone: {tone}
3. Length: {length}
4. Include realistic discount (15-50% off)
5. Create urgency (limited time/stock)
6. Clear call-to-action
7. Include 2-3 emojis

Just write the promotional content, nothing else.""",

        "reel_idea": f"""You are a viral content creator for Pakistani fashion brands.

Task: {instruction}

Product: {style} {clothing}
Season: {season}
Context: {context}

REQUIREMENTS:
1. Video length: 15-30 seconds
2. Scene-by-scene breakdown (4-6 scenes)
3. Hook in first 3 seconds (specify what)
4. Suggest trending audio style
5. Text overlays for each scene
6. End with CTA
7. Length: {length}
8. Make it trendy and shareable

Just write the reel concept, nothing else.""",

        "story_content": f"""You are an Instagram content strategist for Pakistani fashion brands.

Task: {instruction}

Product: {style} {clothing}
Season: {season}

REQUIREMENTS:
1. Create 5 story slides in sequence
2. Each slide: Visual description + Text overlay
3. Include interactive elements (poll on slide 2 or 3, question sticker, slider)
4. Mix product showcase with engagement
5. Final slide: Strong CTA with link mention
6. Length: {length}

Just write the story sequence, nothing else.""",

        "campaign_idea": f"""You are a senior marketing strategist for Pakistani fashion brands.

Task: {instruction}

Product: {style} {clothing}
Season: {season}
Context: {context}

REQUIREMENTS:
1. Campaign name/theme (creative and memorable)
2. Target audience description (demographics, psychographics)
3. Key messaging (3 main points)
4. Content plan:
   - 4 social media post ideas
   - 3-email sequence outline
   - 1 influencer collaboration idea
5. Promotional offer suggestion
6. Timeline: 2-week rollout
7. Length: {length}
8. Make it culturally relevant for Pakistan

Just write the campaign strategy, nothing else.""",

        "launch_announcement": f"""You are a brand communications expert for Pakistani fashion.

Task: {instruction}

Collection: {style} {clothing}
Season: {season}

REQUIREMENTS:
1. {opening_style} - exciting, fresh opener
2. Tone: {tone}
3. Length: {length}
4. Highlight what's new/special
5. Key features (fabric, designs, colors)
6. Availability info
7. Strong call-to-action
8. Include 3-4 emojis

Just write the launch announcement, nothing else.""",

        "email": f"""You are an email marketing specialist for Pakistani fashion brands.

Task: {instruction}

Product: {style} {clothing}
Season: {season}
Context: {context}

REQUIREMENTS:
1. Subject line: Compelling, under 50 characters
2. Preview text: 40-90 characters
3. Greeting: Personalized
4. Body: {length}
5. Tone: {tone}
6. Clear CTA button text
7. Professional sign-off
8. {opening_style} for the email body

Format:
Subject: [text]
Preview: [text]
Body: [email content]
CTA: [button text]

Just write the email, nothing else.""",

        "whatsapp_broadcast": f"""You are a WhatsApp marketing expert for Pakistani fashion brands.

Task: {instruction}

Product: {style} {clothing}
Season: {season}

REQUIREMENTS:
1. Friendly, conversational greeting
2. Length: {length}
3. Include price range in PKR
4. How to order (reply/call/visit)
5. 2-3 emojis naturally placed
6. Personal but professional tone
7. {opening_style}

Just write the WhatsApp message, nothing else.""",

        "slogan": f"""You are a brand strategist creating taglines for Pakistani fashion.

Task: {instruction}

Brand focus: {style} {clothing}
Season: {season}
Context: {context}

REQUIREMENTS:
1. Create exactly 5 different slogans
2. Each slogan: 4-10 words maximum
3. Mix of styles:
   - 1 elegant/sophisticated
   - 1 playful/fun
   - 1 empowering
   - 1 tradition-focused
   - 1 modern/trendy
4. Memorable and brandable
5. Culturally relevant to Pakistan

Format as numbered list 1-5, nothing else.""",

        "influencer_brief": f"""You are an influencer marketing manager for Pakistani fashion brands.

Task: {instruction}

Product: {style} {clothing}
Season: {season}
Context: {context}

REQUIREMENTS:
1. Campaign objective (clear and measurable)
2. Product to feature (description)
3. Key talking points (4-5 points)
4. Content deliverables:
   - Number of posts/stories/reels
   - Content guidelines
5. Hashtags to use (branded + trending)
6. Do's and Don'ts (3 each)
7. Timeline and deadlines
8. Length: {length}

Just write the influencer brief, nothing else.""",

        "marketing_copy": f"""You are a senior copywriter for Pakistani fashion brands.

Task: {instruction}

Product: {style} {clothing}
Season: {season}
Context: {context}

REQUIREMENTS:
1. {opening_style} - compelling headline
2. Tone: {tone}
3. Length: {length}
4. Highlight unique selling points
5. Emotional appeal + practical benefits
6. Strong call-to-action
7. Suitable for website/brochure/ad

Just write the marketing copy, nothing else.""",
    }
    
    return base_prompts.get(content_type, base_prompts["marketing_copy"])


# ============== GENERATOR CLASS ==============

class TrainingDataGeneratorV2:
    def __init__(self, api_keys: list):
        self.api_keys = api_keys
        self.current_key_index = 0
        self.request_count = 0
        self.retry_count = 0
        self.max_retries = 3
        self.all_keys_exhausted = False
        self.keys_exhausted_count = 0
        
        # Enhanced stopping criteria
        self.consecutive_failures = 0
        self.max_consecutive_failures = 10  # Stop after 10 consecutive failures
        self.total_failures = 0
        self.max_total_failures = 50  # Stop after 50 total failures
        self.should_stop = False
        self.stop_reason = None
        
        self.configure_api()
        
    def configure_api(self):
        genai.configure(api_key=self.api_keys[self.current_key_index])
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        print(f"Using API key {self.current_key_index + 1}/{len(self.api_keys)}")
    
    def rotate_key(self) -> bool:
        next_index = (self.current_key_index + 1) % len(self.api_keys)
        if next_index == 0:
            self.keys_exhausted_count += 1
            if self.keys_exhausted_count >= 2:
                print("\n⚠️  All API keys exhausted! Stopping generation.")
                self.all_keys_exhausted = True
                return False
            print(f"\n⚠️  Cycled through all keys. Waiting 60 seconds...")
            time.sleep(60)
        self.current_key_index = next_index
        self.configure_api()
        self.request_count = 0
        return True
    
    def generate_response(self, prompt: str, attempt: int = 0) -> str:
        # Check all stopping conditions
        if self.should_stop or self.all_keys_exhausted:
            return None
        
        if self.consecutive_failures >= self.max_consecutive_failures:
            self.should_stop = True
            self.stop_reason = f"Too many consecutive failures ({self.consecutive_failures})"
            print(f"\n🛑 STOPPING: {self.stop_reason}")
            return None
            
        if self.total_failures >= self.max_total_failures:
            self.should_stop = True
            self.stop_reason = f"Too many total failures ({self.total_failures})"
            print(f"\n🛑 STOPPING: {self.stop_reason}")
            return None
        
        if attempt >= self.max_retries:
            self.consecutive_failures += 1
            self.total_failures += 1
            print(f"\n⚠️  Max retries reached. Failures: {self.consecutive_failures} consecutive, {self.total_failures} total")
            return None
        
        try:
            response = self.model.generate_content(prompt)
            self.request_count += 1
            self.consecutive_failures = 0  # Reset on success
            if self.request_count >= 50 and len(self.api_keys) > 1:
                self.rotate_key()
            return response.text.strip()
        except Exception as e:
            error_msg = str(e).lower()
            print(f"Error: {e}")
            
            # Check for permanent errors (invalid API key)
            if "invalid" in error_msg and "api" in error_msg:
                self.consecutive_failures += 1
                self.total_failures += 1
                print(f"⚠️  Invalid API key. Trying next key...")
                if not self.rotate_key():
                    return None
                return self.generate_response(prompt, attempt + 1)
            
            if "quota" in error_msg or "rate" in error_msg or "429" in error_msg:
                print(f"Rate limit hit (attempt {attempt + 1}/{self.max_retries})...")
                if not self.rotate_key():
                    return None
                time.sleep(5)
                return self.generate_response(prompt, attempt + 1)
            
            # Unknown error
            self.consecutive_failures += 1
            self.total_failures += 1
            return None
    
    def generate_all_datasets(self):
        """Generate all datasets split by category"""
        
        OUTPUT_DIR.mkdir(exist_ok=True)
        
        # Backup existing data
        backup_dir = OUTPUT_DIR / "backup"
        backup_dir.mkdir(exist_ok=True)
        
        print("="*60)
        print("Training Data Generator V2")
        print("Generating varied, high-quality marketing content")
        print("="*60)
        
        total_generated = 0
        
        for category, config in CONTENT_TYPES.items():
            if self.all_keys_exhausted or self.should_stop:
                if self.stop_reason:
                    print(f"\n🛑 Generation stopped: {self.stop_reason}")
                break
                
            target_count = EXAMPLES_CONFIG.get(category, 30)
            output_file = OUTPUT_DIR / config["file"]
            
            print(f"\n{'='*50}")
            print(f"Generating: {category}")
            print(f"Target: {target_count} examples")
            print(f"Output: {output_file}")
            print(f"{'='*50}")
            
            examples = []
            examples_generated = 0
            
            # Calculate weighted distribution
            total_weight = sum(t["weight"] for t in config["types"])
            
            with tqdm(total=target_count, desc=category) as pbar:
                while examples_generated < target_count and not self.all_keys_exhausted and not self.should_stop:
                    # Select content type based on weight
                    content_type_config = random.choices(
                        config["types"],
                        weights=[t["weight"] for t in config["types"]]
                    )[0]
                    
                    content_type = content_type_config["name"]
                    instruction_template = random.choice(content_type_config["instructions"])
                    length = content_type_config["length"]
                    
                    # Random metadata
                    clothing = random.choice(ALL_CLOTHING)
                    season = random.choice(SEASONS)
                    style = random.choice(BRANDS_STYLE)
                    context = random.choice(CONTEXTS)
                    platform = random.choice(PLATFORMS)
                    
                    # Fill instruction template
                    instruction = instruction_template.format(
                        style=style, clothing=clothing, season=season, context=context
                    )
                    
                    # Generate prompt
                    prompt = get_generation_prompt(
                        content_type, instruction, clothing, season, style, context, length
                    )
                    
                    # Get response
                    response = self.generate_response(prompt)
                    
                    if response:
                        example = {
                            "instruction": instruction,
                            "input": "",
                            "output": response,
                            "content_type": content_type,
                            "category": category,
                            "metadata": {
                                "clothing": clothing,
                                "season": season,
                                "style": style,
                                "platform": platform,
                                "context": context,
                                "length_spec": length
                            }
                        }
                        examples.append(example)
                        examples_generated += 1
                        pbar.update(1)
                        
                        # Progressive save every 10 examples
                        if examples_generated % 10 == 0:
                            self._save_examples(output_file, examples)
                            tqdm.write(f"  💾 Saved {len(examples)} examples")
                    
                    time.sleep(WAIT_TIME_SECONDS)
            
            # Final save for this category
            if examples:
                self._save_examples(output_file, examples)
                total_generated += len(examples)
                print(f"✅ {category}: {len(examples)} examples saved")
        
        # Summary
        print("\n" + "="*60)
        print("GENERATION COMPLETE")
        print("="*60)
        print(f"Total examples generated: {total_generated}")
        print(f"\nFiles created in {OUTPUT_DIR}/:")
        for category, config in CONTENT_TYPES.items():
            file_path = OUTPUT_DIR / config["file"]
            if file_path.exists():
                count = sum(1 for _ in open(file_path, 'r', encoding='utf-8'))
                print(f"  ✓ {config['file']}: {count} examples")
    
    def _save_examples(self, file_path: Path, examples: list):
        """Save examples to JSONL file"""
        with open(file_path, 'w', encoding='utf-8') as f:
            for ex in examples:
                f.write(json.dumps(ex, ensure_ascii=False) + '\n')


def main():
    print("="*60)
    print("Training Data Generator V2")
    print("Eastern Clothing Marketing Content")
    print("="*60)
    print("\n💡 TIP: Press Ctrl+C at any time to stop gracefully")
    print("    (Data will be saved before stopping)\n")
    
    if API_KEYS[0] == "YOUR_GEMINI_API_KEY":
        print("\n⚠️  Please add your Gemini API key!")
        print("Get free API key from: https://aistudio.google.com/apikey")
        return
    
    generator = TrainingDataGeneratorV2(API_KEYS)
    
    try:
        generator.generate_all_datasets()
    except KeyboardInterrupt:
        print("\n\n🛑 Keyboard interrupt detected! Stopping gracefully...")
        print("\nℹ️  Data generated so far has been saved.")
        print(f"    Check {OUTPUT_DIR}/ for partial results.")
        return
    
    print("\n✅ Dataset generation complete!")
    print(f"Output directory: {OUTPUT_DIR}")
    print("\nNext steps:")
    print("1. Review the generated data for quality")
    print("2. Run the fine-tuning script with these datasets")


if __name__ == "__main__":
    main()
