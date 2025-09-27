import json
from typing import Dict, Any, List, Optional
import os
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch

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
                dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
            )
            
            # Create pipeline for easier text generation
            self.pipe = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
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
    
    async def process_request(self, user_message: str) -> Dict[str, Any]:
        """
        Process user request using Llama 3.2 with tool calling
        This acts as a generic LLM that can both reason and call tools
        """
        if not self.model_loaded:
            return self._fallback_response(user_message)
        
        try:
            # Create conversation with system context for Llama 3.2
            system_prompt = self._create_system_prompt()
            user_prompt = f"<|start_header_id|>user<|end_header_id|>\n\n{user_message}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
            
            full_prompt = system_prompt + user_prompt
            
            # Use the pipeline for generation with tool calling
            response = self.pipe(
                full_prompt,
                max_new_tokens=512,
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
            
            if tool_call:
                print(f"DEBUG: Tool call detected: {tool_call['name']} with parameters: {tool_call['parameters']}")
                return {
                    "type": "tool_call",
                    "tool": tool_call["name"],
                    "parameters": tool_call["parameters"],
                    "response": llm_response,
                    "reasoning": f"LLM decided to call {tool_call['name']} tool"
                }
            else:
                print("DEBUG: No tool call detected, treating as conversation")
                return {
                    "type": "conversation",
                    "response": llm_response,
                    "reasoning": "LLM provided conversational response"
                }
                
        except Exception as e:
            print(f"Error with Llama 3.2: {e}")
            return self._fallback_response(user_message)
    
    def _create_system_prompt(self) -> str:
        """
        Create system prompt for Llama 3.2 with tool definitions
        """
        tools_json = json.dumps(self.tools, indent=2)
        
        return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are Brandmate, an AI assistant specialized in Eastern clothing brand marketing. You can help users with various marketing tasks and have access to specialized tools.

Available tools:
{tools_json}

You can:
1. Have natural conversations about Eastern clothing brands, marketing strategies, and fashion
2. Call tools when users need specific content generated
3. Provide advice, suggestions, and creative ideas
4. Help with brand strategy and marketing planning

When a user requests content generation (images, text, videos, websites), use the appropriate tool. For general conversation, just respond naturally.

Tool calling format:
<tool_call>
{{
    "name": "tool_name",
    "parameters": {{
        "param1": "value1",
        "param2": "value2"
    }}
}}
</tool_call>

Be helpful, creative, and focus on Eastern clothing brand marketing expertise.<|eot_id|>"""
    
    def _extract_tool_call(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Extract tool call from LLM response
        """
        try:
            # Look for tool call in the response - try both formats
            tool_json = None
            
            # First try the correct format: <tool_call>...</tool_call>
            if "<tool_call>" in response and "</tool_call>" in response:
                start = response.find("<tool_call>") + len("<tool_call>")
                end = response.find("</tool_call>")
                tool_json = response[start:end].strip()
            
            # If not found, try the LLM's format: <image_generation>...</image_generation>
            elif "<image_generation>" in response and "</image_generation>" in response:
                start = response.find("<image_generation>") + len("<image_generation>")
                end = response.find("</image_generation>")
                tool_json = response[start:end].strip()
            
            # If still not found, try other tool formats
            elif "<text_generation>" in response and "</text_generation>" in response:
                start = response.find("<text_generation>") + len("<text_generation>")
                end = response.find("</text_generation>")
                tool_json = response[start:end].strip()
            
            elif "<video_generation>" in response and "</video_generation>" in response:
                start = response.find("<video_generation>") + len("<video_generation>")
                end = response.find("</video_generation>")
                tool_json = response[start:end].strip()
            
            elif "<website_generation>" in response and "</website_generation>" in response:
                start = response.find("<website_generation>") + len("<website_generation>")
                end = response.find("</website_generation>")
                tool_json = response[start:end].strip()
            
            if tool_json:
                print(f"DEBUG: Found tool JSON: {tool_json}")
                tool_call = json.loads(tool_json)
                print(f"DEBUG: Parsed tool call: {tool_call}")
                
                # If the tool call doesn't have a "name" field, infer it from the tag
                if "name" not in tool_call:
                    if "<image_generation>" in response:
                        tool_call["name"] = "image_generation"
                    elif "<text_generation>" in response:
                        tool_call["name"] = "text_generation"
                    elif "<video_generation>" in response:
                        tool_call["name"] = "video_generation"
                    elif "<website_generation>" in response:
                        tool_call["name"] = "website_generation"
                    print(f"DEBUG: Inferred tool name: {tool_call.get('name')}")
                
                # Validate tool call
                available_tools = [tool["name"] for tool in self.tools]
                print(f"DEBUG: Available tools: {available_tools}")
                
                if "name" in tool_call and tool_call["name"] in available_tools:
                    print(f"DEBUG: Tool call validated successfully")
                    return tool_call
                else:
                    print(f"DEBUG: Tool call validation failed - name: {tool_call.get('name')}, available: {available_tools}")
                    
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing tool call: {e}")
        
        return None
    
    def _fallback_response(self, user_message: str) -> Dict[str, Any]:
        """
        Fallback response when model is not available
        """
        message_lower = user_message.lower().strip()
        
        # Simple intent detection for fallback
        if any(phrase in message_lower for phrase in [
            "image", "poster", "banner", "visual", "design", "picture", "photo"
        ]):
            return {
                "type": "tool_call",
                "tool": "image_generation",
                "parameters": {"prompt": user_message, "style": "eastern_clothing"},
                "response": f"I'll help you create an image for: {user_message}",
                "reasoning": "Fallback detected image-related request"
            }
        elif any(phrase in message_lower for phrase in [
            "text", "caption", "copy", "description", "write", "content"
        ]):
            return {
                "type": "tool_call",
                "tool": "text_generation",
                "parameters": {"topic": user_message, "content_type": "marketing_copy"},
                "response": f"I'll help you create text content for: {user_message}",
                "reasoning": "Fallback detected text-related request"
            }
        elif any(phrase in message_lower for phrase in [
            "video", "reel", "animation", "motion", "clip"
        ]):
            return {
                "type": "tool_call",
                "tool": "video_generation",
                "parameters": {"description": user_message, "video_type": "promotional"},
                "response": f"I'll help you create video content for: {user_message}",
                "reasoning": "Fallback detected video-related request"
            }
        elif any(phrase in message_lower for phrase in [
            "website", "landing", "page", "site", "web"
        ]):
            return {
                "type": "tool_call",
                "tool": "website_generation",
                "parameters": {"brand_info": user_message, "page_type": "landing"},
                "response": f"I'll help you create website content for: {user_message}",
                "reasoning": "Fallback detected website-related request"
            }
        else:
            return {
                "type": "conversation",
                "response": f"Hello! I'm Brandmate, your AI assistant for Eastern clothing brand marketing. I can help you create images, text, videos, and websites for your brand. What would you like me to help you with today?",
                "reasoning": "Fallback provided general greeting"
            }
    
    # Legacy method for backward compatibility
    async def analyze_request(self, user_message: str) -> Dict[str, Any]:
        """
        Legacy method - now calls the new process_request method
        """
        result = await self.process_request(user_message)
        
        if result["type"] == "tool_call":
            return {
                "tool": result["tool"],
                "confidence": 0.9,
                "reasoning": result["reasoning"],
                "parameters": result["parameters"],
                "response": result["response"]
            }
        else:
            return {
                "tool": "conversation",
                "confidence": 0.8,
                "reasoning": result["reasoning"],
                "response": result["response"]
            }