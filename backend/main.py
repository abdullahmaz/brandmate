from fastapi import FastAPI, HTTPException, Query, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import os
import uvicorn
import asyncio
import threading
import urllib.parse
import requests as req_lib
from dotenv import load_dotenv
from model_loader import (
    get_llm,
    get_image_generator,
    get_text_generator,
    get_website_generator,
    offload_image_generator,
    offload_text_generator,
    load_llm_at_startup,
)
from services.database_service import database_service
from services.storage_service import storage_service
from services.supabase_client import supabase_client
from services.auth import get_current_user, CurrentUser
from database_models import ChatCreate, ChatResponse, MessageCreate, MessageResponse, ChatWithMessages, MessageRole, MessageType, Chat
from generators.video_generator import VideoGenerator
from services.billboard_scraper import (
    scrape_billboards,
    format_billboard_results,
    enrich_with_contact,
    detect_near_me_query,
    get_city_for_query,
    get_city_from_coordinates,
    extract_city_from_text,
    infer_ad_type_from_text,
    should_trigger_billboard_search,
)

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

# Video generator — stays loaded (no heavy model, just ComfyUI HTTP client)
video_generator = VideoGenerator()  # ← new

class ChatMessage(BaseModel):
    role: str  # "system", "user", "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    chat_id: str | None = None
    conversation_history: list[ChatMessage] = []
    current_city: str | None = None
    current_lat: float | None = None
    current_lon: float | None = None

class MessageRequest(BaseModel):
    message: str
    conversation_history: list[ChatMessage] = []
    image_base64: str | None = None  # ← new: base64-encoded image for I2V
    current_city: str | None = None
    current_lat: float | None = None
    current_lon: float | None = None

class ChatResponse(BaseModel):
    message: str
    image: str | None = None
    html: str | None = None
    tool: str | None = None
    chat_id: str | None = None
    conversation_history: list[ChatMessage] = []


def _extract_client_ip(http_request: Request) -> Optional[str]:
    """Extract client IP, preferring proxy headers when available."""
    forwarded_for = http_request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = http_request.headers.get("x-real-ip", "")
    if real_ip:
        return real_ip.strip()
    return http_request.client.host if http_request.client else None


def _is_placeholder_city(city: str) -> bool:
    """Return True for non-usable placeholder city values produced by the LLM."""
    value = (city or "").strip().lower()
    if not value:
        return True
    placeholders = {
        "your city",
        "city name",
        "my city",
        "current city",
        "near me",
        "unknown",
        "n/a",
        "none",
        "null",
    }
    return value in placeholders


async def _fetch_latest_image_from_chat(db_client, chat_id: str) -> Optional[bytes]:
    """Fetch the most recent generated image from this chat as bytes for I2V."""
    try:
        messages = await database_service.get_messages(db_client, chat_id, limit=50)
        # Walk backwards, find latest message with s3_url and IMAGE type
        for msg in reversed(messages):
            if msg.s3_url and msg.message_type == MessageType.IMAGE:
                import requests as _req
                resp = _req.get(msg.s3_url, timeout=30)
                resp.raise_for_status()
                print(f"DEBUG: Fetched reference image from S3: {msg.s3_url}")
                return resp.content
    except Exception as e:
        print(f"DEBUG: Failed to fetch reference image: {e}")
    return None

async def process_message(
    llm_orchestrator,
    db_client,
    chat_id: str,
    message: str,
    conversation_history: list[ChatMessage],
    image_bytes: bytes = None,
    client_ip: str = None,
    current_city: str = None,
    current_lat: float = None,
    current_lon: float = None,
) -> ChatResponse:
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
        response_html = None
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
                
            elif tool_name == "billboard_search":
                city = result["parameters"].get("city", "")
                ad_type = result["parameters"].get("ad_type", "billboard")

                if _is_placeholder_city(city):
                    city = ""

                # Recover missed fields from raw text if tool params are incomplete.
                if not city:
                    city = extract_city_from_text(message) or ""
                if not ad_type or ad_type == "billboard":
                    ad_type = infer_ad_type_from_text(message)
                
                # If city is empty or user said "near me", try geolocation
                if not city and detect_near_me_query(message):
                    if current_lat is not None and current_lon is not None:
                        detected_city = get_city_from_coordinates(current_lat, current_lon)
                        if detected_city:
                            city = detected_city
                            print(f"DEBUG: Using city from browser coordinates: {city}")
                    elif current_city and not _is_placeholder_city(current_city):
                        city = current_city.strip()
                        print(f"DEBUG: Using city from browser geolocation: {city}")
                    else:
                        detected_city = get_city_for_query(message, client_ip)
                        if detected_city:
                            city = detected_city
                            print(f"DEBUG: Using detected city from IP geolocation: {city}")
                
                if not city:
                    response_message = "Please specify a city to search for billboards (e.g. Lahore, Karachi, Islamabad), or enable location access to use 'near me' search."
                else:
                    try:
                        print(f"DEBUG: Scraping billboards — city={city}, ad_type={ad_type}")
                        scrape_data = scrape_billboards(city=city, ad_type=ad_type, max_pages=2)
                        enrich_with_contact(scrape_data.get("results", []), top_n=3)
                        response_message = format_billboard_results(scrape_data, top_n=5)
                        print(f"DEBUG: Billboard scrape complete — {len(scrape_data.get('results', []))} results")
                    except Exception as scrape_err:
                        print(f"Billboard scrape error: {scrape_err}")
                        response_message = (
                            f"I tried to search for {ad_type} advertising spaces in {city} on adbuq.com, "
                            f"but encountered an issue: {scrape_err}. "
                            f"You can search directly at https://www.adbuq.com/"
                        )

            elif tool_name == "video_generation":
                description = result["parameters"].get("description", message)
                video_type = result["parameters"].get("video_type", "promotional")
                use_reference_image = result["parameters"].get("use_reference_image", False)
                try:
                    if image_bytes:
                        # User attached an image — always use it
                        print(f"DEBUG: Routing to I2V (image attached)")
                        video_data = await video_generator.generate_i2v(
                            prompt=description,
                            image_bytes=image_bytes,
                            video_type=video_type,
                        )
                    elif use_reference_image:
                        # User referred to a previous image — fetch latest from DB
                        print(f"DEBUG: Routing to I2V (reference image from history)")
                        ref_image_bytes = await _fetch_latest_image_from_chat(db_client, chat_id)
                        if ref_image_bytes:
                            video_data = await video_generator.generate_i2v(
                                prompt=description,
                                image_bytes=ref_image_bytes,
                                video_type=video_type,
                            )
                        else:
                            print(f"DEBUG: No reference image found, falling back to T2V")
                            video_data = await video_generator.generate_t2v(
                                prompt=description,
                                video_type=video_type,
                            )
                    else:
                        # Pure text-to-video
                        print(f"DEBUG: Routing to T2V (no image)")
                        video_data = await video_generator.generate_t2v(
                            prompt=description,
                            video_type=video_type,
                        )
                    try:
                        s3_url = await storage_service.store_generated_image(video_data, description)
                        print(f"DEBUG: Video stored in S3: {s3_url}")
                    except Exception as s3_error:
                        print(f"S3 storage error: {s3_error}")
                        s3_url = video_data
                    generated_image = s3_url
                    response_message = "Here's your generated video!"
                    tool_used = "video_generation"
                except Exception as video_error:
                    print(f"Video generation error: {video_error}")
                    response_message = "I encountered an issue generating the video. Please make sure ComfyUI is running and try again."
                
            elif tool_name == "website_generation":
                # One comprehensive prompt; website generator always produces a landing page.
                params = result.get("parameters") or {}
                prompt = params.get("prompt") or params.get("brand_info") or message

                generator, gen_status = get_website_generator()
                if gen_status == "loading":
                    response_message = "The website generator is still loading. Please try again in a moment."
                    tool_used = "loading"
                elif (not generator) or gen_status != "ready" or not getattr(generator, "model_loaded", False):
                    response_message = "Website generation service is currently unavailable."
                else:
                    try:
                        response_html = await generator.generate(prompt=prompt)
                    except Exception as gen_error:
                        print(f"Website generation error: {gen_error}")
                        response_html = None

                    if response_html:
                        response_message = "Here's your landing page."
                    else:
                        response_message = "I had trouble generating the landing page. Please try again with more brand details."
                # WebsiteGenerator uses external inference (HTTP), so we keep it loaded.
                
            else:
                response_message = result["response"]
                
        else:
            # Fallback route: if LLM misses tool-call but user intent is billboard search.
            if should_trigger_billboard_search(message):
                city = extract_city_from_text(message) or ""
                ad_type = infer_ad_type_from_text(message)
                if not city and detect_near_me_query(message):
                    if current_lat is not None and current_lon is not None:
                        detected_city = get_city_from_coordinates(current_lat, current_lon)
                        if detected_city:
                            city = detected_city
                            print(f"DEBUG: Using city from browser coordinates (fallback route): {city}")
                    elif current_city and not _is_placeholder_city(current_city):
                        city = current_city.strip()
                        print(f"DEBUG: Using city from browser geolocation (fallback route): {city}")
                    else:
                        city = get_city_for_query(message, client_ip) or ""

                if city:
                    try:
                        print(f"DEBUG: Billboard fallback scrape — city={city}, ad_type={ad_type}")
                        scrape_data = scrape_billboards(city=city, ad_type=ad_type, max_pages=2)
                        enrich_with_contact(scrape_data.get("results", []), top_n=3)
                        response_message = format_billboard_results(scrape_data, top_n=5)
                        tool_used = "billboard_search"
                    except Exception as scrape_err:
                        print(f"Billboard fallback scrape error: {scrape_err}")
                        response_message = (
                            f"I tried to search for {ad_type} advertising spaces in {city} on adbuq.com, "
                            f"but encountered an issue: {scrape_err}. "
                            f"You can search directly at https://www.adbuq.com/"
                        )
                        tool_used = "billboard_search"
                else:
                    response_message = "Please specify a city to search for billboards (e.g. Lahore, Karachi, Islamabad), or set DEFAULT_BILLBOARD_CITY for near-me fallback in local development."
                    tool_used = "billboard_search"
            else:
                # Generic conversation response
                response_message = result["response"]
                tool_used = "conversation"
        
        # Save assistant message
        try:
            message_type = storage_service.get_message_type_from_tool(tool_used) if tool_used != "conversation" else MessageType.TEXT
            msg_metadata = None
            if tool_used == "website_generation" and response_html:
                msg_metadata = {"html": response_html}
            await database_service.create_message(db_client, MessageCreate(
                chat_id=chat_id,
                role=MessageRole.ASSISTANT,
                content=response_message,
                message_type=message_type,
                s3_url=s3_url,
                metadata=msg_metadata
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
            html=response_html,
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

@app.get("/api/convert-video")
async def convert_video(url: str = Query(...)):
    """Fetch a WEBP video from S3 and convert it to MP4 using ffmpeg, then stream it back."""
    import tempfile, os, subprocess
    import imageio_ffmpeg

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Invalid URL scheme")
    try:
        # Fetch WEBP from S3
        resp = req_lib.get(url, timeout=60)
        resp.raise_for_status()
        webp_bytes = resp.content

        # Extract frames from animated WEBP using Pillow, then encode to MP4 with ffmpeg
        from PIL import Image
        import io as _io

        with tempfile.TemporaryDirectory() as tmpdir:
            mp4_path = os.path.join(tmpdir, "output.mp4")

            # Extract all frames from animated WEBP
            img = Image.open(_io.BytesIO(webp_bytes))
            frames = []
            try:
                while True:
                    frame = img.copy().convert("RGB")
                    frames.append(frame)
                    img.seek(img.tell() + 1)
            except EOFError:
                pass

            if not frames:
                raise HTTPException(status_code=500, detail="No frames found in WEBP")

            print(f"DEBUG: Extracted {len(frames)} frames from animated WEBP")

            # Save frames as PNG files
            frame_paths = []
            for i, frame in enumerate(frames):
                frame_path = os.path.join(tmpdir, f"frame_{i:04d}.png")
                frame.save(frame_path)
                frame_paths.append(frame_path)

            # Encode frames to MP4 with ffmpeg at 16fps (ComfyUI default)
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            frame_pattern = os.path.join(tmpdir, "frame_%04d.png")
            result = subprocess.run(
                [
                    ffmpeg_exe, "-y",
                    "-framerate", "8",
                    "-i", frame_pattern,
                    "-vcodec", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                    mp4_path
                ],
                capture_output=True
            )
            print(f"DEBUG: ffmpeg stderr: {result.stderr.decode()}")
            if result.returncode != 0:
                raise HTTPException(status_code=500, detail=f"Video conversion failed: {result.stderr.decode()}")

            with open(mp4_path, "rb") as f:
                mp4_bytes = f.read()

            print(f"DEBUG: MP4 size: {len(mp4_bytes)} bytes")

        return StreamingResponse(
            iter([mp4_bytes]),
            media_type="video/mp4",
            headers={"Content-Disposition": "attachment; filename=video.mp4"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not convert video: {e}")

@app.get("/api/image-proxy")
async def image_proxy(url: str = Query(...)):
    """Proxy images from external sources (e.g. adbuq.com) to bypass hotlink protection."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Invalid URL scheme")
    try:
        resp = req_lib.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.adbuq.com/",
            },
            timeout=10,
            stream=True,
        )
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "image/jpeg")
        return StreamingResponse(resp.iter_content(chunk_size=8192), media_type=content_type)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not fetch image: {e}")


@app.post("/api/chats", response_model=ChatResponse)
async def create_chat(
    request: ChatCreate,
    user: CurrentUser = Depends(get_current_user),
):
    """Create a new chat owned by the authenticated user."""
    try:
        db_client = supabase_client.client_for_user(user.access_token)
        chat = await database_service.create_chat(db_client, user_id=user.id, chat_data=request)
        return ChatResponse(
            message="Chat created successfully",
            tool="chat_created",
            chat_id=chat.id
        )
    except Exception as e:
        print(f"Error creating chat: {e}")
        raise HTTPException(status_code=500, detail="Failed to create chat")

@app.post("/api/chats/{chat_id}/messages", response_model=ChatResponse)
async def send_message(
    chat_id: str,
    request: MessageRequest,
    http_request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    """Send a message to a chat the user owns."""
    try:
        db_client = supabase_client.client_for_user(user.access_token)

        # Decode base64 image to bytes if present (for I2V)
        image_bytes = None
        if request.image_base64:
            import base64 as _base64
            image_bytes = _base64.b64decode(request.image_base64)
            print(f"DEBUG: Image received ({len(image_bytes)} bytes)")

        # Verify chat exists AND belongs to caller (RLS scopes the lookup).
        chat = await database_service.get_chat(db_client, chat_id)
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
            user_image_s3 = None
            if image_bytes:
                try:
                    import base64 as _b64
                    img_b64 = f"data:image/jpeg;base64,{_b64.b64encode(image_bytes).decode()}"
                    user_image_s3 = await storage_service.store_generated_image(img_b64, "user_upload")
                    print(f"DEBUG: User image stored in S3: {user_image_s3}")
                except Exception as s3_err:
                    print(f"DEBUG: Failed to store user image: {s3_err}")

            user_message = await database_service.create_message(db_client, MessageCreate(
                chat_id=chat_id,
                role=MessageRole.USER,
                content=request.message,
                message_type=MessageType.TEXT,
                s3_url=user_image_s3
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
        
        # Extract client IP for geolocation
        client_ip = _extract_client_ip(http_request)

        return await process_message(
            llm_orchestrator,
            db_client,
            chat_id,
            request.message,
            request.conversation_history,
            image_bytes,
            client_ip,
            request.current_city,
            request.current_lat,
            request.current_lon,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in send_message: {e}")
        raise HTTPException(status_code=500, detail="Failed to send message")

@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    http_request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    try:
        db_client = supabase_client.client_for_user(user.access_token)

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
                chat = await database_service.create_chat(db_client, user_id=user.id, chat_data=chat_data)
                chat_id = chat.id

            # Save user message
            user_message = await database_service.create_message(db_client, MessageCreate(
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
                        await database_service.create_message(db_client, MessageCreate(
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
            await database_service.create_message(db_client, MessageCreate(
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
        
        # Extract client IP for geolocation
        client_ip = _extract_client_ip(http_request)

        return await process_message(
            llm_orchestrator,
            db_client,
            chat_id,
            request.message,
            request.conversation_history,
            None,
            client_ip,
            request.current_city,
            request.current_lat,
            request.current_lon,
        )

    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return ChatResponse(
            message=f"Sorry, I encountered an error processing your request. Please try again with a different question.",
            tool="error"
        )

@app.get("/api/chats", response_model=list[Chat])
async def get_chats(
    limit: int = 50,
    user: CurrentUser = Depends(get_current_user),
):
    """Get all chats owned by the authenticated user (RLS-scoped)."""
    try:
        db_client = supabase_client.client_for_user(user.access_token)
        chats = await database_service.get_chats(db_client, limit=limit)
        return chats
    except Exception as e:
        print(f"Error getting chats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve chats")

@app.get("/api/chats/{chat_id}", response_model=ChatWithMessages)
async def get_chat(
    chat_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get a specific chat with all its messages. RLS scopes ownership."""
    try:
        db_client = supabase_client.client_for_user(user.access_token)
        chat = await database_service.get_chat_with_messages(db_client, chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        return chat
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting chat: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve chat")

@app.get("/api/chats/{chat_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    chat_id: str,
    limit: int = 100,
    user: CurrentUser = Depends(get_current_user),
):
    """Get messages for a specific chat. RLS scopes ownership."""
    try:
        db_client = supabase_client.client_for_user(user.access_token)
        messages = await database_service.get_messages(db_client, chat_id, limit=limit)
        return messages
    except Exception as e:
        print(f"Error getting messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve messages")

@app.put("/api/chats/{chat_id}/title")
async def update_chat_title(
    chat_id: str,
    title: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Update chat title (caller must own the chat)."""
    try:
        db_client = supabase_client.client_for_user(user.access_token)
        success = await database_service.update_chat_title(db_client, chat_id, title)
        if not success:
            raise HTTPException(status_code=404, detail="Chat not found")
        return {"message": "Chat title updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating chat title: {e}")
        raise HTTPException(status_code=500, detail="Failed to update chat title")

@app.delete("/api/chats/{chat_id}")
async def delete_chat(
    chat_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Delete a chat and all its messages (caller must own the chat)."""
    try:
        db_client = supabase_client.client_for_user(user.access_token)

        # Verify chat exists AND belongs to caller (RLS scopes the lookup).
        chat = await database_service.get_chat(db_client, chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")

        success = await database_service.delete_chat(db_client, chat_id)
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