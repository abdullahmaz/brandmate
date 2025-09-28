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
                dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                use_safetensors=True,    # Faster loading with safetensors
            )
            
            # Create pipeline for easier text generation
            self.pipe = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                batch_size=1,  # Process one at a time for memory efficiency
                return_tensors="pt"  # Return PyTorch tensors for better performance
            )
            
            print("Llama 3.2 3B Instruct loaded successfully!")
            self.model_loaded = True
            
            # Enable memory optimization
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                print(f"GPU memory cleared. Available: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
            
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
            return self._fallback_response(user_message, conversation_history)
        
        try:
            # Build conversation following HF format
            conversation = self._build_conversation(user_message, conversation_history)
            
            # Convert conversation to Llama 3.2 format
            full_prompt = self._conversation_to_llama_format(conversation)
            
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
            return self._fallback_response(user_message, conversation_history)
    
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
        tools_json = json.dumps(self.tools, indent=2)
        
        return f"""You are Brandmate, an AI assistant specialized in Eastern clothing brand marketing. You can help users with various marketing tasks and have access to specialized tools.

Available tools:
{tools_json}

You can:
1. Have natural conversations about Eastern clothing brands, marketing strategies, and fashion
2. Call tools when users need specific content generated
3. Provide advice, suggestions, and creative ideas
4. Help with brand strategy and marketing planning

When a user requests content generation (images, text, videos, websites), use the appropriate tool. For general conversation, just respond naturally.

IMPORTANT: When you call a tool, do it ONCE and do it correctly. Do not explain that you should have called a tool or try to correct yourself. Just call the tool directly.

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

Be helpful, creative, and focus on Eastern clothing brand marketing expertise."""
    
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
                
                # Fix tool call structure - ensure parameters are properly nested
                if "name" in tool_call:
                    # If parameters are at the root level, move them to a parameters object
                    if "parameters" not in tool_call:
                        parameters = {}
                        for key, value in tool_call.items():
                            if key != "name":
                                parameters[key] = value
                        tool_call = {
                            "name": tool_call["name"],
                            "parameters": parameters
                        }
                        print(f"DEBUG: Restructured tool call: {tool_call}")
                
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
    
    def _clean_response_for_conversation(self, response: str) -> str:
        """
        Clean the LLM response for conversation history by removing tool calls
        """
        # Remove tool call blocks
        import re
        
        # Remove <tool_call>...</tool_call> blocks
        cleaned = re.sub(r'<tool_call>.*?</tool_call>', '', response, flags=re.DOTALL)
        
        # Remove other tool-related tags that might appear
        cleaned = re.sub(r'<image_generation>.*?</image_generation>', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'<text_generation>.*?</text_generation>', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'<video_generation>.*?</video_generation>', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'<website_generation>.*?</website_generation>', '', cleaned, flags=re.DOTALL)
        
        # Clean up extra whitespace
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)
        cleaned = cleaned.strip()
        
        return cleaned if cleaned else "I'll help you with that request."
    
    def _fallback_response(self, user_message: str, conversation_history: list = None) -> Dict[str, Any]:
        """
        Fallback response when model is not available
        """
        message_lower = user_message.lower().strip()
        
        # Build conversation for fallback
        conversation = []
        if conversation_history:
            conversation.extend(conversation_history)
        
        # Add current user message
        conversation.append({"role": "user", "content": user_message})
        
        # Simple intent detection for fallback
        if any(phrase in message_lower for phrase in [
            "image", "poster", "banner", "visual", "design", "picture", "photo"
        ]):
            response_msg = f"I'll help you create an image for: {user_message}"
            conversation.append({"role": "assistant", "content": response_msg})
            return {
                "type": "tool_call",
                "tool": "image_generation",
                "parameters": {"prompt": user_message, "style": "eastern_clothing"},
                "response": response_msg,
                "reasoning": "Fallback detected image-related request",
                "conversation_history": conversation
            }
        elif any(phrase in message_lower for phrase in [
            "text", "caption", "copy", "description", "write", "content"
        ]):
            response_msg = f"I'll help you create text content for: {user_message}"
            conversation.append({"role": "assistant", "content": response_msg})
            return {
                "type": "tool_call",
                "tool": "text_generation",
                "parameters": {"topic": user_message, "content_type": "marketing_copy"},
                "response": response_msg,
                "reasoning": "Fallback detected text-related request",
                "conversation_history": conversation
            }
        elif any(phrase in message_lower for phrase in [
            "video", "reel", "animation", "motion", "clip"
        ]):
            response_msg = f"I'll help you create video content for: {user_message}"
            conversation.append({"role": "assistant", "content": response_msg})
            return {
                "type": "tool_call",
                "tool": "video_generation",
                "parameters": {"description": user_message, "video_type": "promotional"},
                "response": response_msg,
                "reasoning": "Fallback detected video-related request",
                "conversation_history": conversation
            }
        elif any(phrase in message_lower for phrase in [
            "website", "landing", "page", "site", "web"
        ]):
            response_msg = f"I'll help you create website content for: {user_message}"
            conversation.append({"role": "assistant", "content": response_msg})
            return {
                "type": "tool_call",
                "tool": "website_generation",
                "parameters": {"brand_info": user_message, "page_type": "landing"},
                "response": response_msg,
                "reasoning": "Fallback detected website-related request",
                "conversation_history": conversation
            }
        else:
            response_msg = f"Hello! I'm Brandmate, your AI assistant for Eastern clothing brand marketing. I can help you create images, text, videos, and websites for your brand. What would you like me to help you with today?"
            conversation.append({"role": "assistant", "content": response_msg})
            return {
                "type": "conversation",
                "response": response_msg,
                "reasoning": "Fallback provided general greeting",
                "conversation_history": conversation
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