from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import asyncio
import threading
from dotenv import load_dotenv
from model_loader import get_llm, get_image_generator, get_text_generator, offload_image_generator, offload_text_generator, load_llm_at_startup
from database_service import database_service
from storage_service import storage_service
from database_models import ChatCreate, ChatResponse, MessageCreate, MessageResponse, ChatWithMessages, MessageRole, MessageType, Chat

load_dotenv()

app = FastAPI(title="Brandmate API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# LLM loads at startup and stays loaded. Image/Text load on demand and offload after use.
print("Starting Brandmate server... (LLM loading at startup; Image/Text load on demand)")
threading.Thread(target=load_llm_at_startup, daemon=True).start()

class ChatMessage(BaseModel):
    role: str  # "system", "user", "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    chat_id: str | None = None
    conversation_history: list[ChatMessage] = []

class MessageRequest(BaseModel):
    message: str
    conversation_history: list[ChatMessage] = []

class ChatResponse(BaseModel):
    message: str
    image: str | None = None
    tool: str | None = None
    chat_id: str | None = None
    conversation_history: list[ChatMessage] = []

async def process_message(llm_orchestrator, chat_id: str, message: str, conversation_history: list[ChatMessage]) -> ChatResponse:
    """Process a message and return response. Image/Text models are loaded on demand when needed."""
    try:
        # Convert conversation history to list of dicts for LLM orchestrator
        history = []
        for msg in conversation_history:
            history.append({
                "role": msg.role,
                "content": msg.content
            })
        
        print(f"DEBUG: Processing message: {message}")
        print(f"DEBUG: Conversation history length: {len(history)}")
        for i, msg in enumerate(history):
            print(f"DEBUG: History {i}: {msg['role']} - {msg['content'][:100]}...")
        
        # Use the LLM orchestrator to process the request with conversation history
        result = await llm_orchestrator.process_request(message, history)
        
        response_message = ""
        generated_image = None
        tool_used = None
        s3_url = None
        
        if result["type"] == "tool_call":
            tool_name = result["tool"]
            tool_used = tool_name
            
            if tool_name == "image_generation":
                # Free text-model VRAM before loading image model (swap strategy).
                # This keeps the image model warm for consecutive image requests.
                offload_text_generator()
                image_generator, img_status = get_image_generator()
                if img_status == "loading":
                    response_message = "The image model is still loading. Please try again in a moment."
                    tool_used = "loading"
                elif image_generator and img_status == "ready":
                    try:
                        # Extract prompt from parameters or use the original message
                        prompt = result["parameters"].get("prompt", message)
                        style = result["parameters"].get("style", "eastern_clothing")
                        
                        # Generate image using local Stable Diffusion
                        generated_image = await image_generator.generate_image(
                            prompt=prompt,
                            style=style
                        )
                        
                        # Store image in S3
                        try:
                            print(f"DEBUG: Attempting to store image in S3...")
                            s3_url = await storage_service.store_generated_image(generated_image, prompt)
                            print(f"DEBUG: S3 URL generated: {s3_url}")
                        except Exception as s3_error:
                            print(f"S3 storage error: {s3_error}")
                            s3_url = generated_image  # Fallback to base64
                            print(f"DEBUG: Using fallback base64 image")
                        
                        response_message = f"I've generated an image for your request: '{prompt}'. The image showcases Eastern clothing design elements as requested."
                        # Image model stays loaded — no offload here.
                    except Exception as img_error:
                        print(f"Image generation error: {img_error}")
                        response_message = f"I tried to generate an image for '{prompt}', but encountered a technical issue. Here's some information instead: {result['response']}"
                else:
                    response_message = "Image generation service is currently unavailable."
                
            elif tool_name == "text_generation":
                # Free image-model VRAM before loading text model (swap strategy).
                # This keeps the text model warm for consecutive text requests.
                offload_image_generator()
                prompt = result["parameters"].get("prompt", message)
                text_generator, txt_status = get_text_generator()
                if txt_status == "loading":
                    response_message = "The text generation model is still loading. Please try again in a moment."
                    tool_used = "loading"
                elif text_generator and txt_status == "ready" and text_generator.model_loaded:
                    try:
                        generated_text = await text_generator.generate_content(
                            prompt=prompt,
                        )
                        response_message = generated_text
                        # Text model stays loaded — no offload here.
                    except Exception as text_error:
                        print(f"Text generation error: {text_error}")
                        response_message = f"I tried to generate content based on your request, but encountered an issue."
                else:
                    response_message = f"Text generation service is currently unavailable."
                
            elif tool_name == "video_generation":
                description = result["parameters"].get("description", message)
                video_type = result["parameters"].get("video_type", "promotional")
                response_message = f"I'll help you create a {video_type} video for: {description}. This feature is coming soon!"
                
            elif tool_name == "website_generation":
                brand_info = result["parameters"].get("brand_info", message)
                page_type = result["parameters"].get("page_type", "landing")
                response_message = f"I'll help you create a {page_type} page for: {brand_info}. This feature is coming soon!"
                
            else:
                response_message = result["response"]
                
        else:
            # Generic conversation response
            response_message = result["response"]
            tool_used = "conversation"
        
        # Save assistant message
        try:
            message_type = storage_service.get_message_type_from_tool(tool_used) if tool_used != "conversation" else MessageType.TEXT
            await database_service.create_message(MessageCreate(
                chat_id=chat_id,
                role=MessageRole.ASSISTANT,
                content=response_message,
                message_type=message_type,
                s3_url=s3_url
            ))
        except Exception as db_error:
            print(f"Database error saving assistant message: {db_error}")
            # Continue without saving to database
        
        # Convert conversation history back to ChatMessage objects
        updated_conversation = []
        if "conversation_history" in result:
            for msg in result["conversation_history"]:
                updated_conversation.append(ChatMessage(
                    role=msg["role"],
                    content=msg["content"]
                ))
        
        return ChatResponse(
            message=response_message,
            image=s3_url if s3_url else generated_image,
            tool=tool_used,
            chat_id=chat_id,
            conversation_history=updated_conversation
        )
        
    except Exception as e:
        print(f"Error in process_message: {e}")
        return ChatResponse(
            message=f"Sorry, I encountered an error processing your request. Please try again with a different question.",
            tool="error",
            chat_id=chat_id
        )

@app.get("/")
async def root():
    return {"message": "Brandmate API is running!"}


@app.post("/api/chats", response_model=ChatResponse)
async def create_chat(request: ChatCreate):
    """Create a new chat"""
    try:
        chat = await database_service.create_chat(request)
        return ChatResponse(
            message="Chat created successfully",
            tool="chat_created",
            chat_id=chat.id
        )
    except Exception as e:
        print(f"Error creating chat: {e}")
        raise HTTPException(status_code=500, detail="Failed to create chat")

@app.post("/api/chats/{chat_id}/messages", response_model=ChatResponse)
async def send_message(chat_id: str, request: MessageRequest):
    """Send a message to an existing chat"""
    try:
        # Verify chat exists
        chat = await database_service.get_chat(chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        # Get LLM (loads on first use). If loading, ask user to wait.
        llm_orchestrator, llm_status = get_llm()
        if llm_status == "loading":
            return ChatResponse(
                message="The AI models are still loading. This may take a few minutes on first use. Please wait and try again shortly.",
                tool="loading"
            )
        if llm_status == "failed" and llm_orchestrator is None:
            image_generator, img_status = get_image_generator()
            if img_status != "ready" or image_generator is None:
                return ChatResponse(
                    message="Service components failed to initialize. Please check server logs for details.",
                    tool="error"
                )
        
        # Save user message
        try:
            user_message = await database_service.create_message(MessageCreate(
                chat_id=chat_id,
                role=MessageRole.USER,
                content=request.message,
                message_type=MessageType.TEXT
            ))
        except Exception as db_error:
            error_msg = str(db_error)
            if "RLS policy" in error_msg:
                print(f"RLS policy error: {db_error}")
                return ChatResponse(
                    message="Database security policy is blocking operations. Please check your Supabase RLS settings or run the disable_rls.sql script.",
                    tool="error"
                )
            else:
                print(f"Database error: {db_error}")
                pass
        
        if llm_orchestrator is None:
            return ChatResponse(
                message="The language model is unavailable. Image generation may be available in a new chat.",
                tool="limited",
                chat_id=chat_id
            )
        
        return await process_message(llm_orchestrator, chat_id, request.message, request.conversation_history)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in send_message: {e}")
        raise HTTPException(status_code=500, detail="Failed to send message")

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Get LLM (loads on first use). If loading, ask user to wait.
        llm_orchestrator, llm_status = get_llm()
        if llm_status == "loading":
            return ChatResponse(
                message="The AI models are still loading. This may take a few minutes on first use. Please wait and try again shortly.",
                tool="loading"
            )
        if llm_status == "failed" and llm_orchestrator is None:
            image_generator, img_status = get_image_generator()
            if img_status != "ready" or image_generator is None:
                return ChatResponse(
                    message="Service components failed to initialize. Please check server logs for details.",
                    tool="error"
                )
        
        # Get or create chat
        chat_id = request.chat_id
        try:
            if not chat_id:
                # Create new chat
                chat_data = ChatCreate(title=request.message[:50] + "..." if len(request.message) > 50 else request.message)
                chat = await database_service.create_chat(chat_data)
                chat_id = chat.id
            
            # Save user message
            user_message = await database_service.create_message(MessageCreate(
                chat_id=chat_id,
                role=MessageRole.USER,
                content=request.message,
                message_type=MessageType.TEXT
            ))
        except Exception as db_error:
            error_msg = str(db_error)
            if "RLS policy" in error_msg:
                print(f"RLS policy error: {db_error}")
                return ChatResponse(
                    message="Database security policy is blocking operations. Please check your Supabase RLS settings or run the disable_rls.sql script.",
                    tool="error"
                )
            else:
                print(f"Database error: {db_error}")
                chat_id = chat_id or "temp-chat"
        
        # If LLM is not available but image generator is, we can still handle some requests
        if llm_orchestrator is None:
            image_generator, img_status = get_image_generator()
            if img_status == "ready" and image_generator and any(word in request.message.lower() for word in ["image", "picture", "photo", "design"]):
                try:
                    generated_image = await image_generator.generate_image(
                        prompt=request.message,
                        style="eastern_clothing"
                    )
                    try:
                        s3_url = await storage_service.store_generated_image(generated_image, request.message)
                    except Exception as s3_error:
                        print(f"S3 storage error: {s3_error}")
                        s3_url = generated_image
                    try:
                        await database_service.create_message(MessageCreate(
                            chat_id=chat_id,
                            role=MessageRole.ASSISTANT,
                            content="I've generated an image based on your request. The LLM service is currently unavailable, so I couldn't analyze your request in detail.",
                            message_type=MessageType.IMAGE,
                            s3_url=s3_url
                        ))
                    except Exception as db_error:
                        print(f"Database error saving fallback message: {db_error}")
                    return ChatResponse(
                        message="I've generated an image based on your request. The LLM service is currently unavailable, so I couldn't analyze your request in detail.",
                        image=s3_url,
                        tool="image_generation",
                        chat_id=chat_id
                    )
                except Exception as img_error:
                    print(f"Image generation error in fallback mode: {img_error}")
                finally:
                    # Delete the local reference BEFORE offloading so the GC can
                    # immediately reclaim VRAM when offload() calls gc.collect().
                    del image_generator
                    offload_image_generator()
            await database_service.create_message(MessageCreate(
                chat_id=chat_id,
                role=MessageRole.ASSISTANT,
                content="I'm currently operating with limited functionality. The language model is still initializing or unavailable. You can try simple image generation requests or check back later.",
                message_type=MessageType.TEXT
            ))
            return ChatResponse(
                message="I'm currently operating with limited functionality. The language model is still initializing or unavailable. You can try simple image generation requests or check back later.",
                tool="limited",
                chat_id=chat_id
            )
        
        return await process_message(llm_orchestrator, chat_id, request.message, request.conversation_history)
        
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return ChatResponse(
            message=f"Sorry, I encountered an error processing your request. Please try again with a different question.",
            tool="error"
        )

@app.get("/api/chats", response_model=list[Chat])
async def get_chats(user_id: str = None, limit: int = 50):
    """Get all chats, optionally filtered by user_id"""
    try:
        chats = await database_service.get_chats(user_id=user_id, limit=limit)
        return chats
    except Exception as e:
        print(f"Error getting chats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve chats")

@app.get("/api/chats/{chat_id}", response_model=ChatWithMessages)
async def get_chat(chat_id: str):
    """Get a specific chat with all its messages"""
    try:
        chat = await database_service.get_chat_with_messages(chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        return chat
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting chat: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve chat")

@app.get("/api/chats/{chat_id}/messages", response_model=list[MessageResponse])
async def get_messages(chat_id: str, limit: int = 100):
    """Get messages for a specific chat"""
    try:
        messages = await database_service.get_messages(chat_id, limit=limit)
        return messages
    except Exception as e:
        print(f"Error getting messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve messages")

@app.put("/api/chats/{chat_id}/title")
async def update_chat_title(chat_id: str, title: str):
    """Update chat title"""
    try:
        success = await database_service.update_chat_title(chat_id, title)
        if not success:
            raise HTTPException(status_code=404, detail="Chat not found")
        return {"message": "Chat title updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating chat title: {e}")
        raise HTTPException(status_code=500, detail="Failed to update chat title")

@app.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: str):
    """Delete a chat and all its messages"""
    try:
        # Verify chat exists first
        chat = await database_service.get_chat(chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        # Delete the chat and all its messages
        success = await database_service.delete_chat(chat_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete chat")
        
        return {"message": "Chat deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting chat: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete chat")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
