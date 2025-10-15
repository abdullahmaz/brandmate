# Brandmate Backend

FastAPI backend for the Brandmate AI-powered brand automation platform with intelligent tool calling and multimodal AI capabilities.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- 8GB+ RAM (16GB recommended)
- 10GB+ storage for models
- NVIDIA GPU with 8GB+ VRAM (recommended)
- Hugging Face account and token (required)
- Supabase account (optional - for chat persistence)
- AWS account with S3 (optional - for image storage)

### Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup environment:**
   ```bash
   cp env_example.txt .env
   # Edit .env with your configuration:
   # - HF_TOKEN: Your Hugging Face token (REQUIRED)
   # - SUPABASE_URL & SUPABASE_ANON_KEY: For chat persistence (optional)
   # - AWS credentials: For S3 image storage (optional)
   ```

3. **Run the server:**
   ```bash
   python main.py
   ```
   
   **Note:** AI models will be downloaded automatically on first run. This may take several minutes depending on your internet connection.

The API will be available at `http://localhost:8000`

## 📡 API Endpoints

### Core Endpoints

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| `GET` | `/` | Health check | - | `{"message": "Brandmate API is running!"}` |
| `POST` | `/api/chat` | Legacy chat endpoint with tool calling | `{"message": "string", "chat_id": "string?", "conversation_history": []}` | `{"message": "string", "image": "string", "tool": "string", "chat_id": "string"}` |
| `POST` | `/api/chats` | Create a new chat | `{"title": "string?", "user_id": "string?"}` | Chat object |
| `GET` | `/api/chats` | Get all chats | Query: `user_id`, `limit` | Array of chat objects |
| `GET` | `/api/chats/{chat_id}` | Get chat with messages | - | Chat with messages |
| `POST` | `/api/chats/{chat_id}/messages` | Send message to chat | `{"message": "string", "conversation_history": []}` | Response with generated content |
| `GET` | `/api/chats/{chat_id}/messages` | Get chat messages | Query: `limit` | Array of messages |
| `PUT` | `/api/chats/{chat_id}/title` | Update chat title | Query: `title` | Success message |
| `DELETE` | `/api/chats/{chat_id}` | Delete chat and messages | - | Success message |

### Request/Response Examples

**Chat Request:**
```json
{
  "message": "Create a poster for my summer lawn collection"
}
```

**Chat Response:**
```json
{
  "message": "I've generated an image for your request: 'Create a poster for my summer lawn collection'. The image showcases Eastern clothing design elements as requested.",
  "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "tool": "image_generation"
}
```

## 🏗️ Architecture

### Core Components

```
backend/
├── main.py                # FastAPI server and API endpoints
├── llm_orchestrator.py    # LLM orchestration and tool calling
├── image_generator.py     # Image generation using OpenJourney
├── database_models.py     # Pydantic models for database entities
├── database_service.py    # Database operations with Supabase
├── storage_service.py     # File storage operations with AWS S3
├── supabase_client.py     # Supabase client initialization
├── s3_client.py           # AWS S3 client initialization
├── requirements.txt       # Python dependencies
├── env_example.txt        # Environment variables template
└── README.md
```

### LLM Orchestrator (`llm_orchestrator.py`)

The brain of the system that handles:
- **Natural Language Understanding**: Processes user requests
- **Tool Selection**: Intelligently chooses appropriate tools
- **Context Management**: Maintains conversation context
- **Response Generation**: Creates human-like responses

**Key Features:**
- Uses Llama 3.2 3B Instruct for intelligent reasoning
- Native tool calling capabilities
- Context-aware responses
- Fallback to rule-based analysis

### Image Generator (`image_generator.py`)

Handles visual content creation:
- **Model**: OpenJourney (Midjourney-style fine-tuned model)
- **Specialization**: Eastern clothing and traditional wear
- **Output**: Base64-encoded PNG images or S3 URLs
- **Optimization**: GPU acceleration when available

**Key Features:**
- High-quality Midjourney-style image generation
- Eastern clothing specialization with prompt enhancement
- Automatic S3 storage integration
- Error handling and fallback placeholder generation

### Database Service (`database_service.py`)

Manages data persistence with Supabase:
- **Database**: PostgreSQL via Supabase
- **Operations**: Create, read, update, delete chats and messages
- **Models**: Chat sessions and conversation history

**Key Features:**
- Chat session management
- Message history persistence
- User-based filtering
- RLS policy error handling

### Storage Service (`storage_service.py`)

Manages cloud storage with AWS S3:
- **Storage**: AWS S3 for generated images
- **Features**: Automatic URL generation, public access control
- **Fallback**: Base64 encoding when S3 unavailable

**Key Features:**
- Image upload to S3
- Public URL generation
- Content type detection
- Error handling with fallbacks

## 🤖 AI Models

### LLM Model: Llama 3.2 3B Instruct
- **Parameters**: 3B total
- **Provider**: Meta AI
- **Capabilities**: Reasoning, tool calling, conversation
- **Specialization**: General purpose with native tool calling
- **Memory**: ~6GB storage requirement
- **Context**: Maintains conversation history

### Image Model: OpenJourney
- **Provider**: PromptHero
- **Type**: Text-to-image generation (Midjourney-style)
- **Specialization**: High-quality artistic images with "mdjrny-v4 style" prefix
- **Output**: 512x512 PNG images
- **Enhancement**: Automatic prompt enhancement for Eastern clothing

## 🛠️ Tool Calling System

The LLM can intelligently call these tools based on user requests:

### Available Tools

| Tool | Description | Input | Output |
|------|-------------|-------|--------|
| `image_generation` | Create visual content | Text prompt | Base64 image |
| `text_generation` | Generate marketing copy | Context + requirements | Text content |
| `video_generation` | Create promotional videos | Script + style | Video file |
| `website_generation` | Build web content | Requirements + content | HTML/CSS |

### Tool Calling Flow

1. **User Request** → LLM analyzes intent
2. **Tool Selection** → LLM chooses appropriate tool(s)
3. **Tool Execution** → Selected tool processes request
4. **Response Generation** → LLM formats response with results
5. **Return to User** → Structured response with generated content

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with these variables:

```env
# Hugging Face Configuration (REQUIRED)
HF_TOKEN=your_huggingface_token_here

# Supabase Configuration (Optional - for chat persistence)
SUPABASE_URL=your_supabase_url_here
SUPABASE_ANON_KEY=your_supabase_anon_key_here

# AWS S3 Configuration (Optional - for image storage)
AWS_ACCESS_KEY_ID=your_aws_access_key_id_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key_here
AWS_REGION=us-east-1
S3_BUCKET_NAME=your_s3_bucket_name_here

# Model Configuration (Optional)
MODEL_CACHE_DIR=./models

# Server Configuration (Optional)
HOST=0.0.0.0
PORT=8000
DEBUG=False
```

**Important Notes:**
- **HF_TOKEN** is required to download and use AI models from Hugging Face
- **Supabase** credentials enable chat history persistence; without them, chats work but aren't saved
- **AWS S3** credentials enable permanent image storage; without them, images are returned as base64 data URLs
- All models are downloaded automatically on first run if not cached

### Model Configuration

**Llama 3.2 3B Instruct Settings:**
```python
MODEL_CONFIG = {
    "model_name": "meta-llama/Llama-3.2-3B-Instruct",
    "max_length": 2048,
    "temperature": 0.7,
    "top_p": 0.9,
    "repetition_penalty": 1.1
}
```

**OpenJourney Settings:**
```python
IMAGE_CONFIG = {
    "model_id": "prompthero/openjourney",
    "num_inference_steps": 20,
    "guidance_scale": 7.5,
    "width": 512,
    "height": 512,
    "prompt_prefix": "mdjrny-v4 style"
}
```

## 🔧 Development

### Running in Development Mode

```bash
# With auto-reload
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# With debug logging
DEBUG=True python main.py
```

### Testing the API

```bash
# Health check
curl http://localhost:8000/

# Chat endpoint
curl -X POST "http://localhost:8000/api/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "Create a poster for my brand"}'
```

### Debugging

Enable debug mode by setting `DEBUG=True` in your environment:
- Detailed logging
- Error stack traces
- Model loading information
- Tool calling details

## 📊 Performance

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 8GB | 16GB+ |
| Storage | 10GB | 20GB+ SSD |
| GPU | Optional | NVIDIA 8GB+ VRAM |
| CPU | 4 cores | 8+ cores |

### Performance Optimization

**GPU Acceleration:**
- Automatically detects and uses available GPUs
- Falls back to CPU if GPU unavailable
- Supports multiple GPU configurations

**Memory Management:**
- Model caching and lazy loading
- Memory-efficient inference
- Automatic cleanup of unused models

**Response Times:**
- Image generation: 3-10 seconds (GPU) / 15-30 seconds (CPU)
- Image upload to S3: 1-2 seconds (if configured)
- Text generation: 1-2 seconds
- Tool selection: <1 second
- Database operations: <500ms (if configured)

## 🚨 Error Handling

### Common Issues

**Model Loading Errors:**
- Ensure HF_TOKEN is set in .env file
- Check internet connection for model downloads
- Verify you have enough disk space (10GB+)
- Check Hugging Face model access permissions

```python
# Check if models are properly initialized
python -c "from llm_orchestrator import LLMOrchestrator; from image_generator import ImageGenerator; print('Models loaded successfully')"
```

**Memory Issues:**
- Reduce batch size
- Use CPU instead of GPU
- Close other applications

**API Errors:**
- Check environment variables
- Verify model paths
- Check server logs

### Error Responses

```json
{
  "error": "Model loading failed",
  "message": "Unable to load Llama 3.2 3B Instruct model. Please check your installation.",
  "code": "MODEL_LOAD_ERROR"
}
```

## 🔒 Security

### API Security
- Input validation with Pydantic
- Rate limiting (configurable)
- CORS configuration
- Error message sanitization

### Model Security
- Local model execution (no data sent to external APIs)
- Secure model storage
- Access control for model files

## 📈 Monitoring

### Health Checks
- Model loading status
- Memory usage monitoring
- GPU utilization tracking
- Response time metrics

### Logging
- Structured logging with timestamps
- Request/response logging
- Error tracking and reporting
- Performance metrics

## 🚀 Deployment

### Production Setup

```bash
# Install production dependencies
pip install -r requirements.txt

# Set production environment
export DEBUG=False
export HOST=0.0.0.0
export PORT=8000

# Run with Gunicorn (recommended)
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "main.py"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues and questions:
- Check the logs in `logs/` directory
- Review the API documentation at `/docs`
- Create an issue in the repository
- Contact the development team

## 📄 License

This project is part of the Final Year Project at FAST NUCES, Islamabad.
