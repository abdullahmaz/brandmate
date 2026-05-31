import json
from typing import Dict, Any, List, Optional
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch

from json_repair import repair_json

class LLMOrchestrator:
    def __init__(self, device: Optional[str] = None):
        # Use Llama 3.2 3B Instruct for fast loading and good tool calling
        model_name = "meta-llama/Llama-3.2-3B-Instruct"
        use_cuda = (device == "cuda") if device else torch.cuda.is_available()
        print(f"Loading Llama 3.2 3B Instruct model: {model_name} (device={device or ('cuda' if use_cuda else 'cpu')})")
        
        try:
            # Load tokenizer first
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            # Load model with appropriate settings for 3B model.
            # Try Flash Attention 2 first (Ampere+ GPU); fall back silently if unavailable.
            extra_kwargs = {}
            if use_cuda:
                try:
                    import flash_attn  # noqa: F401
                    extra_kwargs["attn_implementation"] = "flash_attention_2"
                    print("[LLM] Flash Attention 2 enabled.")
                except ImportError:
                    pass

            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if use_cuda else torch.float32,
                device_map="auto" if use_cuda else None,
                use_safetensors=True,
                **extra_kwargs,
            )
            if not use_cuda and self.model is not None:
                self.model = self.model.to("cpu")
            
            # Create pipeline for easier text generation.
            # device must be set explicitly — without it, transformers auto-detects
            # CUDA and silently moves the model to GPU even when we loaded it on CPU.
            pipe_kwargs = dict(
                model=self.model,
                tokenizer=self.tokenizer,
                dtype=torch.float16 if use_cuda else torch.float32,
            )
            if use_cuda:
                pipe_kwargs["device_map"] = "auto"
            else:
                pipe_kwargs["device"] = "cpu"
            self.pipe = pipeline("text-generation", **pipe_kwargs)
            
            print("Llama 3.2 3B Instruct loaded successfully!")
            self.model_loaded = True
            
        except Exception as e:
            print(f"Error loading Llama 3.2 3B Instruct: {e}")
            print("Falling back to simpler model...")
            self.model_loaded = False
            self.pipe = None
            self.tokenizer = None
            self.model = None
        
        # Define available tools for the LLM
        self.tools = self._define_tools()
    
    def _define_tools(self) -> List[Dict[str, Any]]:
        """
        Define available tools for the LLM to choose from
        """
        return [
            {
                "name": "image_generation",
                "description": "Generate visual content like posters, banners, product images, marketing visuals for Eastern clothing brands",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "Description of the image to generate"
                        },
                        "style": {
                            "type": "string",
                            "description": "Style of Eastern clothing (summer_collection, winter_collection, formal_wear, casual_wear)",
                            "default": "eastern_clothing"
                        }
                    },
                    "required": ["prompt"]
                }
            },
            {
                "name": "text_generation",
                "description": "Generate written content like captions, descriptions, marketing copy, slogans, emails, proposals, campaigns, and outreach material for Eastern clothing brands",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "A comprehensive prompt describing what text content to generate, including the type (caption, description, marketing_copy, slogan, email, proposal, campaign plan, WhatsApp outreach, ad copy, etc.), the subject matter, target audience, tone, length, and any specific requirements"
                        }
                    },
                    "required": ["prompt"]
                }
            },
            {
                "name": "video_generation",
                "description": "Generate video content like reels, animations, promotional videos for Eastern clothing brands",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "video_type": {
                            "type": "string",
                            "description": "Type of video (reel, promotional, animation)",
                            "default": "promotional"
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the video to create"
                        },
                        "use_reference_image": {
                            "type": "boolean",
                            "description": "Set to true if the user wants to animate an attached/current/previously generated image from this conversation. Set to false only for pure text-to-video requests.",
                            "default": False
                        }
                    },
                    "required": ["description"]
                }
            },
            {
                "name": "website_generation",
                "description": "Generate website content like landing pages, online presence for Eastern clothing brands",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "One comprehensive prompt containing all important brand/product info and requirements. If details are missing, the website generator should make reasonable assumptions."
                        }
                    },
                    "required": ["prompt"]
                }
            },
            {
                "name": "billboard_search",
                "description": "Search for real physical billboard and OOH (Out-of-Home) advertising spaces in Pakistani cities. Use this when users want to physically market their brand outdoors, find billboard locations, check advertising prices, or look for digital/static/pole signs in a specific city.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "The Pakistani city to search billboards in (e.g. Lahore, Karachi, Islamabad, Rawalpindi)"
                        },
                        "ad_type": {
                            "type": "string",
                            "description": "Type of OOH media: billboard, digital, pole, airport, bridge, bus shelter, smd, vehicle branding, wall panels. Default is billboard.",
                            "default": "billboard"
                        }
                    },
                    "required": ["city"]
                }
            }
        ]
    
    async def process_request(self, user_message: str, conversation_history: list = None,) -> Dict[str, Any]:
        """
        Process user request using Llama 3.2 with tool calling and conversation history
        This follows the Hugging Face Conversations approach
        """
        if not self.model_loaded:
            return None
        
        try:
            # Build conversation following HF format
            conversation = self._build_conversation(user_message, conversation_history)
            
            # Convert conversation to Llama 3.2 format
            full_prompt = self._conversation_to_llama_format(conversation)
            
            # Use the pipeline for generation with tool calling
            # Low temperature (0.1-0.3) improves reliable JSON/tool-call format; high temp causes malformed brackets
            response = self.pipe(
                full_prompt,
                max_new_tokens=2048,
                temperature=0.2,
                do_sample=True,
                return_full_text=False,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            # Extract the response
            llm_response = response[0]["generated_text"]
            
            # Parse the response to check for tool calls
            tool_call = self._extract_tool_call(llm_response)
            
            print(f"DEBUG: LLM Response: {llm_response}")
            print(f"DEBUG: Extracted tool call: {tool_call}")
            
            # Add assistant response to conversation (clean version without tool calls)
            clean_response = self._clean_response_for_conversation(llm_response)
            conversation.append({"role": "assistant", "content": clean_response})
            
            if tool_call:
                print(f"DEBUG: Tool call detected: {tool_call['name']} with parameters: {tool_call['parameters']}")
                return {
                    "type": "tool_call",
                    "tool": tool_call["name"],
                    "parameters": tool_call["parameters"],
                    "response": llm_response,
                    "reasoning": f"LLM decided to call {tool_call['name']} tool",
                    "conversation_history": conversation
                }
            else:
                print("DEBUG: No tool call detected, treating as conversation")
                return {
                    "type": "conversation",
                    "response": llm_response,
                    "reasoning": "LLM provided conversational response",
                    "conversation_history": conversation
                }
                
        except Exception as e:
            print(f"Error with Llama 3.2: {e}")
            return None
    
    def _build_conversation(self, user_message: str, conversation_history: list = None) -> list:
        """
        Build conversation following Hugging Face format
        """
        conversation = []
        
        # Add system message
        conversation.append({
            "role": "system", 
            "content": self._create_system_content()
        })
        
        # Add conversation history if provided.
        # Cap to the last 10 messages to prevent input-token bloat that
        # slows down each successive request.
        MAX_HISTORY = 10
        if conversation_history:
            # Filter out system messages from history (we handle system separately)
            filtered = [m for m in conversation_history if m.get("role") != "system"]
            for msg in filtered[-MAX_HISTORY:]:
                conversation.append(msg)
        
        # Add current user message
        conversation.append({
            "role": "user",
            "content": user_message
        })
        
        return conversation
    
    def _conversation_to_llama_format(self, conversation: list) -> str:
        """
        Convert Hugging Face conversation format to Llama 3.2 format
        """
        llama_prompt = "<|begin_of_text|>"
        
        for message in conversation:
            role = message["role"]
            content = message["content"]
            
            if role == "system":
                llama_prompt += f"<|start_header_id|>system<|end_header_id|>\n\n{content}<|eot_id|>"
            elif role == "user":
                llama_prompt += f"<|start_header_id|>user<|end_header_id|>\n\n{content}<|eot_id|>"
            elif role == "assistant":
                llama_prompt += f"<|start_header_id|>assistant<|end_header_id|>\n\n{content}<|eot_id|>"
        
        # Add assistant header for response
        llama_prompt += "<|start_header_id|>assistant<|end_header_id|>\n\n"
        
        return llama_prompt
    
    def _create_system_content(self) -> str:
        """
        Create system content for conversation (without Llama formatting)
        """

        return """
        
        You are Brandmate, an AI assistant for Eastern clothing brand marketing.

        Guardrails:
        - Use only these tool tags: <image_generation>, <text_generation>, <video_generation>, <website_generation>, <billboard_search>. Never invent new tool names or tags.
        - If a request is harmful, illegal, hateful, explicit sexual content, or violent wrongdoing, refuse briefly and do not call any tool.
        - Do not fabricate factual details (prices, availability, locations, contacts, results, or brand claims). If data is missing, ask a concise clarifying question or state assumptions explicitly.
        - Keep outputs brand-safe, professional, and culturally respectful for Pakistani/Eastern clothing audiences.
        - Protect privacy: do not request or reveal sensitive personal data unless strictly needed for the task.

        When users ask for images/posters/visuals, use:
        <image_generation>
        {"parameters": {"prompt": "description", "style": "eastern_clothing"}}

        When users ask for any writing deliverable, route it to text_generation. This includes captions, ad copy, campaign ideas, campaign plans, content calendars, client emails, outreach emails, proposals, pitch decks (text content), product descriptions, taglines, scripts, and similar marketing/business writing.
        Use:
        <text_generation>
        {"parameters": {"prompt": "Prompt that describes the content to generate based on the user's request"}}
        
        Example of a good prompt: "Create a marketing_copy for a new summer lawn collection targeting modern Pakistani women. The content should be elegant and sophisticated, include cultural references to Eid and festive seasons, use relevant emojis and hashtags like #PakistaniFashion #LawnCollection, emphasize quality and craftsmanship. The collection features floral prints, pastel colors, and lightweight cotton fabric suitable for hot weather."

        Modesty rules for ALL video descriptions: clothing MUST be modest, fully-covered Eastern clothing (shalwar kameez, kurta, lawn suits, lehenga with full dupatta coverage). NEVER describe revealing, tight, suggestive, or skin-exposing imagery. NEVER describe western dress, swimwear, lingerie, or bare skin. Always describe full sleeves, modest necklines, and dupatta covering the chest. Keep descriptions family-friendly, professional, and appropriate for an Eastern fashion brand. NEVER mention duration in seconds (the video model produces a fixed short clip).

        For TEXT-TO-VIDEO (use_reference_image: false), expand the user's request into a rich, single-paragraph description. Include: camera movement (slow pan, tracking shot, static, zoom), lighting (golden hour, soft studio light, dramatic shadows, natural daylight), color palette, subject motion and expression, background/environment details, and quality cues (4K, cinematic, high detail, smooth motion). Use:
        <video_generation>
        {"parameters": {"description": "faithful user intent with light enhancement", "video_type": "promotional", "use_reference_image": false}}

        For IMAGE-TO-VIDEO (use_reference_image: true) — when the user refers to a previously generated image ("that image", "this image", "animate it", "make a video of it", "use that photo") — write a SHORT description (1-2 sentences, max ~40 words). Describe ONLY motion and camera movement. DO NOT re-describe the clothing, model, scene, or background — those come from the reference image and re-describing them causes the video to drift away from the source. DO NOT add new objects, locations, or props that aren't in the image. Good examples: "The model walks forward toward the camera and gives a small twirl, then poses with hands on hips. Slow camera push-in.", "She turns her head slowly and smiles. Static camera.", "She walks across the frame from left to right at a relaxed pace. Camera tracks her gently.". Use:
        <video_generation>
        {"parameters": {"description": "short motion-only description", "video_type": "promotional", "use_reference_image": true}}

        When users ask for websites, use:
        <website_generation>
        {"parameters": {"prompt": "brand details + any requirements (landing page; assume missing details)"}}

        When users want to physically market their brand, find billboards, outdoor advertising, OOH media, digital signs, pole signs, or any physical advertising space in a Pakistani city, use:
        <billboard_search>
        {"parameters": {"city": "city name", "ad_type": "billboard"}}

        Examples that should trigger billboard_search:
        - "I want to physically market my brand in Lahore" → city=Lahore, ad_type=billboard
        - "Find digital billboards in Karachi" → city=Karachi, ad_type=digital
        - "Show me pole signs in Islamabad" → city=Islamabad, ad_type=pole
        - "Outdoor advertising in Rawalpindi" → city=Rawalpindi, ad_type=billboard

        For general conversation, just respond normally. Always call tools directly without explanations.

        """

    def _parse_tool_json(self, tool_json: str) -> Optional[Dict[str, Any]]:
        """Parse tool JSON; on failure try json_repair for malformed output (missing brackets, trailing commas, etc.)."""
        try:
            return json.loads(tool_json)
        except json.JSONDecodeError:
            if repair_json:
                try:
                    repaired = repair_json(tool_json)
                    return json.loads(repaired)
                except (json.JSONDecodeError, Exception) as e:
                    print(f"json_repair failed: {e}")
            return None

    def _extract_tool_call(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Extract tool call from LLM response
        """
        # Check for old format first: <tool_call>...</tool_call>
        if "<tool_call>" in response:
            try:
                start = response.find("<tool_call>") + len("<tool_call>")
                end = response.find("</tool_call>")
                if end == -1:
                    tool_json = response[start:].strip()
                else:
                    tool_json = response[start:end].strip()
                tool_call = self._parse_tool_json(tool_json)
                if tool_call:
                    available_tools = [tool["name"] for tool in self.tools]
                    if tool_call.get("name") in available_tools:
                        return tool_call
            except (KeyError, TypeError) as e:
                print(f"Error parsing tool_call: {e}")
        
        # Check for new format: <image_generation>, <text_generation>, etc.
        tool_tags = ["<image_generation>", "<text_generation>", "<video_generation>", "<website_generation>", "<billboard_search>"]
        
        for tag in tool_tags:
            if tag in response:
                try:
                    start = response.find(tag) + len(tag)
                    raw = response[start:].strip()
                    # Extract JSON: from first '{' take balanced braces (handles multi-line); if truncated, repair_json can fix
                    first_brace = raw.find('{')
                    if first_brace >= 0:
                        depth = 0
                        for i, c in enumerate(raw[first_brace:], start=first_brace):
                            if c == '{':
                                depth += 1
                            elif c == '}':
                                depth -= 1
                                if depth == 0:
                                    tool_json = raw[first_brace : i + 1]
                                    break
                        else:
                            tool_json = raw[first_brace:]  # truncated, no matching close
                    else:
                        tool_json = raw
                    tool_call = self._parse_tool_json(tool_json)
                    if tool_call:
                        tool_name = tag[1:-1]
                        tool_call["name"] = tool_name
                        available_tools = [tool["name"] for tool in self.tools]
                        if tool_name in available_tools:
                            return tool_call
                except (KeyError, TypeError) as e:
                    print(f"Error parsing {tag}: {e}")
                    continue
        
        return None
    
    def _clean_response_for_conversation(self, response: str) -> str:
        """
        Clean the LLM response for conversation history by removing tool calls
        """
        import re
        
        # Remove tool-specific tags and their content
        tool_tags = ["<image_generation>", "<text_generation>", "<video_generation>", "<website_generation>", "<billboard_search>"]
        cleaned = response
        
        for tag in tool_tags:
            # Remove the tag and everything after it on the same line
            cleaned = re.sub(f'{re.escape(tag)}.*$', '', cleaned, flags=re.MULTILINE)
        
        # Clean up extra whitespace
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)
        cleaned = cleaned.strip()
        
        return cleaned if cleaned else "I'll help you with that request."