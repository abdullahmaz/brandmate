import json
from typing import Dict, Any, List, Optional
import os
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch
import gc

class LLMOrchestrator:
    def __init__(self):
        # Use Llama 3.2 3B Instruct for fast loading and good tool calling
        model_name = "meta-llama/Llama-3.2-3B-Instruct"
        print(f"Loading Llama 3.2 3B Instruct model: {model_name}")
        
        try:
            # Load tokenizer first
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            # Load model with appropriate settings for 3B model
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                use_safetensors=True,
            )
            
            # Create pipeline for easier text generation
            self.pipe = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            )
            
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
                "description": "Generate written content like captions, descriptions, marketing copy, slogans for Eastern clothing brands",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content_type": {
                            "type": "string",
                            "description": "Type of text content (caption, description, marketing_copy, slogan)",
                            "default": "marketing_copy"
                        },
                        "topic": {
                            "type": "string",
                            "description": "Topic or product to write about"
                        }
                    },
                    "required": ["topic"]
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
                        "page_type": {
                            "type": "string",
                            "description": "Type of page (landing, product, about, contact)",
                            "default": "landing"
                        },
                        "brand_info": {
                            "type": "string",
                            "description": "Brand information and requirements"
                        }
                    },
                    "required": ["brand_info"]
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
            response = self.pipe(
                full_prompt,
                max_new_tokens=2048,
                temperature=0.7,
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
        
        # Add conversation history if provided
        if conversation_history:
            # Filter out system messages from history (we handle system separately)
            for msg in conversation_history:
                if msg.get("role") != "system":
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
        
You are Brandmate, an AI assistant specializing in Eastern clothing brand marketing.

Your goals are to:
- Understand the user's brand, audience, and channel.
- Generate effective, on-brand marketing assets.
- Use the appropriate tools for images, text, videos, and websites as described below.

Always:
- Keep responses clear, practical, and action-oriented.
- Adapt tone and style to the requested channel (e.g., Instagram, Facebook, email, website, SMS).
- Ask brief clarifying questions if the user's request is ambiguous or missing critical details (e.g., target audience, platform, language, tone).
- Respect cultural nuances and sensitivities relevant to Eastern clothing and modest fashion.

TOOL USAGE
You have access to the following tools. Use them whenever they are the best way to fulfill the user's request.

1) IMAGE GENERATION  
Use this when the user asks for any kind of **visual / graphic asset**, such as: images, posters, visuals, banners, social posts, ads, product shots, lookbook images, hero images, thumbnails, moodboards, etc.

Call:

<image_generation>
{"parameters": {"prompt": "description", "style": "eastern_clothing"}}

2) TEXT GENERATION  
**MANDATORY** - Use this tool when the user asks you to CREATE, WRITE, or GENERATE any written marketing content, including but not limited to:
- Social media captions (Instagram, Facebook, Twitter, TikTok)
- Email content and newsletters
- Product descriptions
- Marketing copy and ad text
- Blog posts and articles
- Slogans and taglines
- Website copy and landing page text
- SMS marketing messages
- Press releases
- Brand descriptions and bios
- Collection descriptions
- Campaign messaging
- Proposals, pitches, briefs, marketing documents, marketing campagins.
- Any other written marketing material

**IMPORTANT**: If the user asks you to "write", "create", "generate", "make", "draft", "compose", or "come up with" any text content, you MUST call this tool. Do NOT write the content yourself.

Call:

<text_generation>
{"parameters": {"topic": "subject or detailed description of what to write about (If provided, should have details about brand as well)", "content_type": "caption|email|product_description|marketing_copy|slogan|blog_post|etc"}}

3) VIDEO GENERATION  
Use this when the user asks for **video-related assets** such as: video concepts, promotional videos, ad videos, reels, TikTok content, lookbook videos, product showcase videos, etc.

Call:

<video_generation>
{"parameters": {"description": "concise but detailed description of the desired video content, including brand, product, setting, style, and platform", "video_type": "promotional"}}

4) WEBSITE GENERATION  
Use this when the user asks for **website or page-related content/layout**, such as: landing pages, homepages, product pages, collection pages, campaign microsites, or basic brand websites.

Call:

<website_generation>
{"parameters": {"brand_info": "key details about the brand, products, audience, and positioning", "page_type": "short description of the page type, e.g. 'landing', 'homepage', 'product_page', 'collection_page'"}}

GENERAL CONVERSATION (NO TOOL CALLS)
Only respond conversationally (without tools) when the user is:
- Requesting feedback on existing content they've shared
- Having a casual conversation
- Asking clarifying questions about your capabilities

**REMEMBER**: If the user asks you to CREATE, WRITE, or GENERATE anything, you MUST use a tool. Do not generate content in your conversational response.

TOOL CALL FORMAT
- When you decide to use a tool, **respond with the tool call only**, using exactly the tag and JSON format shown above.
- Do **not** add any extra natural language before or after the tool call.

**CRITICAL**: The JSON must be complete and valid. Always close all braces and brackets. Example:
  <text_generation>
  {"parameters": {"topic": "complete topic description", "content_type": "proposal"}}
  
  Notice: The JSON has closing braces for both the "parameters" object and the outer object.

If you are uncertain which tool to use, ask one short clarifying question. Otherwise, choose the single most appropriate tool based on the user's primary requested output.

"""
    
    
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
                
                tool_call = json.loads(tool_json)
                available_tools = [tool["name"] for tool in self.tools]
                if tool_call.get("name") in available_tools:
                    return tool_call
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error parsing tool_call: {e}")
        
        # Check for new format: <image_generation>, <text_generation>, etc.
        tool_tags = ["<image_generation>", "<text_generation>", "<video_generation>", "<website_generation>"]
        
        for tag in tool_tags:
            if tag in response:
                try:
                    start = response.find(tag) + len(tag)
                    tool_json = response[start:].strip()
                    
                    if '\n' in tool_json:
                        tool_json = tool_json.split('\n')[0]
                    
                    tool_call = json.loads(tool_json)
                    tool_name = tag[1:-1]
                    tool_call["name"] = tool_name
                    
                    available_tools = [tool["name"] for tool in self.tools]
                    if tool_name in available_tools:
                        return tool_call
                        
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Error parsing {tag}: {e}")
                    continue
        
        return None
    
    def _clean_response_for_conversation(self, response: str) -> str:
        """
        Clean the LLM response for conversation history by removing tool calls
        """
        import re
        
        # Remove tool-specific tags and their content
        tool_tags = ["<image_generation>", "<text_generation>", "<video_generation>", "<website_generation>"]
        cleaned = response
        
        for tag in tool_tags:
            # Remove the tag and everything after it on the same line
            cleaned = re.sub(f'{re.escape(tag)}.*$', '', cleaned, flags=re.MULTILINE)
        
        # Clean up extra whitespace
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)
        cleaned = cleaned.strip()
        
        return cleaned if cleaned else "I'll help you with that request."