from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import asyncio
import threading
from dotenv import load_dotenv
from llm_orchestrator import LLMOrchestrator
from image_generator import ImageGenerator

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

# Global variables for components
llm_orchestrator = None
image_generator = None
initialization_status = "starting"

def initialize_components_background():
    """Initialize components in a background thread"""
    global llm_orchestrator, image_generator, initialization_status
    
    print("Starting background initialization of components...")
    initialization_status = "loading"
    
    # Try to initialize LLM orchestrator
    try:
        print("Loading LLM Orchestrator...")
        llm_orchestrator = LLMOrchestrator()
        print("LLM Orchestrator initialized successfully!")
    except Exception as e:
        print(f"Error initializing LLM Orchestrator: {e}")
        print("Chat features will operate in fallback mode.")
        llm_orchestrator = None

    # Try to initialize image generator separately
    try:
        print("Loading Image Generator...")
        image_generator = ImageGenerator()
        print("Image Generator initialized successfully!")
    except Exception as e:
        print(f"Error initializing Image Generator: {e}")
        print("Image generation will use placeholder images.")
        image_generator = None

    # Update status
    if llm_orchestrator is not None or image_generator is not None:
        initialization_status = "ready"
        print("Background initialization completed successfully!")
    else:
        initialization_status = "failed"
        print("WARNING: All components failed to initialize. Service will run with limited functionality.")

# Start background initialization
print("Starting Brandmate server...")
threading.Thread(target=initialize_components_background, daemon=True).start()

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    message: str
    image: str | None = None
    tool: str | None = None

@app.get("/")
async def root():
    return {"message": "Brandmate API is running!"}

@app.get("/health")
async def health_check():
    """Simple health check that doesn't depend on models"""
    return {
        "status": "healthy",
        "message": "Server is running",
        "initialization_status": initialization_status
    }

@app.get("/api/status")
async def get_status():
    """Get the current status of the API and its components"""
    return {
        "status": initialization_status,
        "llm_available": llm_orchestrator is not None,
        "image_generator_available": image_generator is not None,
        "message": {
            "starting": "Components are starting to load...",
            "loading": "Components are still loading in the background...",
            "ready": "All components are ready!",
            "failed": "Some components failed to load, but basic functionality is available."
        }.get(initialization_status, "Unknown status")
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Check initialization status
        if initialization_status == "loading":
            return ChatResponse(
                message="The AI models are still loading in the background. This may take several minutes on first startup. Please wait and try again in a few minutes. The server is running but the AI components need more time to initialize.",
                tool="loading"
            )
        
        # Check if any components are available
        if not llm_orchestrator and not image_generator:
            return ChatResponse(
                message="Service components failed to initialize. Please check server logs for details.",
                tool="error"
            )
        
        # If LLM is not available but image generator is, we can still handle some requests
        if not llm_orchestrator:
            # Simple fallback for image requests
            if any(word in request.message.lower() for word in ["image", "picture", "photo", "design"]):
                try:
                    if image_generator:
                        generated_image = await image_generator.generate_image(
                            prompt=request.message,
                            style="eastern_clothing"
                        )
                        return ChatResponse(
                            message="I've generated an image based on your request. The LLM service is currently unavailable, so I couldn't analyze your request in detail.",
                            image=generated_image,
                            tool="image_generation"
                        )
                except Exception as img_error:
                    print(f"Image generation error in fallback mode: {img_error}")
            
            # General fallback message
            return ChatResponse(
                message="I'm currently operating with limited functionality. The language model is still initializing or unavailable. You can try simple image generation requests or check back later.",
                tool="limited"
            )
        
        # Use the LLM orchestrator to process the request
        result = await llm_orchestrator.process_request(request.message)
        
        response_message = ""
        generated_image = None
        tool_used = None
        
        if result["type"] == "tool_call":
            tool_name = result["tool"]
            tool_used = tool_name
            
            if tool_name == "image_generation" and image_generator:
                try:
                    # Extract prompt from parameters or use the original message
                    prompt = result["parameters"].get("prompt", request.message)
                    style = result["parameters"].get("style", "eastern_clothing")
                    
                    # Generate image using local Stable Diffusion
                    generated_image = await image_generator.generate_image(
                        prompt=prompt,
                        style=style
                    )
                    response_message = f"I've generated an image for your request: '{prompt}'. The image showcases Eastern clothing design elements as requested."
                except Exception as img_error:
                    print(f"Image generation error: {img_error}")
                    response_message = f"I tried to generate an image for '{prompt}', but encountered a technical issue. Here's some information instead: {result['response']}"
                
            elif tool_name == "text_generation":
                topic = result["parameters"].get("topic", request.message)
                content_type = result["parameters"].get("content_type", "marketing_copy")
                response_message = f"I'll help you create {content_type} content about: {topic}. This feature is coming soon!"
                
            elif tool_name == "video_generation":
                description = result["parameters"].get("description", request.message)
                video_type = result["parameters"].get("video_type", "promotional")
                response_message = f"I'll help you create a {video_type} video for: {description}. This feature is coming soon!"
                
            elif tool_name == "website_generation":
                brand_info = result["parameters"].get("brand_info", request.message)
                page_type = result["parameters"].get("page_type", "landing")
                response_message = f"I'll help you create a {page_type} page for: {brand_info}. This feature is coming soon!"
                
            else:
                response_message = result["response"]
                
        else:
            # Generic conversation response
            response_message = result["response"]
            tool_used = "conversation"
        
        return ChatResponse(
            message=response_message,
            image=generated_image,
            tool=tool_used
        )
        
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return ChatResponse(
            message=f"Sorry, I encountered an error processing your request. Please try again with a different question.",
            tool="error"
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
