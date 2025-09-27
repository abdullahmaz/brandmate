# Brandmate Backend

FastAPI backend for the Brandmate AI-powered brand automation platform with intelligent tool calling and multimodal AI capabilities.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- 8GB+ RAM (16GB recommended)
- 10GB+ storage for models
- NVIDIA GPU with 8GB+ VRAM (recommended)

### Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup environment:**
   ```bash
   cp env_example.txt .env
   # Edit .env with your configuration
   ```

3. **Download models:**
   ```bash
   python install_models.py  # Downloads all required models
   # OR download specific models:
   python install_gpt_oss.py
   ```

4. **Run the server:**
   ```bash
   python main.py
   ```

The API will be available at `http://localhost:8000`

## 📡 API Endpoints

### Core Endpoints

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| `GET` | `/` | Health check | - | `{"status": "healthy"}` |
| `POST` | `/api/chat` | Main chat endpoint with tool calling | `{"message": "string"}` | `{"message": "string", "image": "base64", "tool": "string"}` |
| `GET` | `/docs` | Interactive API documentation | - | Swagger UI |
| `GET` | `/redoc` | Alternative API documentation | - | ReDoc UI |

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
├── main.py                 # FastAPI server and API endpoints
├── llm_orchestrator.py    # LLM orchestration and tool calling
├── image_generator.py     # Image generation using Stable Diffusion
├── install_models.py      # Model installation and setup
├── install_gpt_oss.py     # GPT-OSS model installation
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
- **Model**: Stable Diffusion v1.5
- **Specialization**: Eastern clothing and traditional wear
- **Output**: Base64-encoded PNG images
- **Optimization**: GPU acceleration when available

**Key Features:**
- High-quality image generation
- Eastern clothing specialization
- Batch processing support
- Error handling and fallbacks

## 🤖 AI Models

### LLM Model: Llama 3.2 3B Instruct
- **Parameters**: 3B total
- **Capabilities**: Reasoning, tool calling, conversation
- **Specialization**: General purpose with tool calling
- **Memory**: ~6GB storage requirement

### Image Model: Stable Diffusion v1.5
- **Provider**: RunwayML
- **Type**: Text-to-image generation
- **Specialization**: General purpose, fine-tunable
- **Output**: 512x512 PNG images

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
# Hugging Face Configuration
HUGGINGFACE_API_TOKEN=your_token_here

# Model Configuration
MODEL_CACHE_DIR=./models
LLAMA_MODEL_PATH=meta-llama/Llama-3.2-3B-Instruct
STABLE_DIFFUSION_MODEL=runwayml/stable-diffusion-v1-5

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=False

# GPU Configuration
CUDA_VISIBLE_DEVICES=0
USE_GPU=True
```

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

**Stable Diffusion Settings:**
```python
IMAGE_CONFIG = {
    "model_id": "runwayml/stable-diffusion-v1-5",
    "num_inference_steps": 50,
    "guidance_scale": 7.5,
    "width": 512,
    "height": 512
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
- Text generation: 1-2 seconds
- Tool selection: <1 second

## 🚨 Error Handling

### Common Issues

**Model Loading Errors:**
```python
# Check if models are properly installed
python -c "from llm_orchestrator import LLMOrchestrator; print('Models loaded successfully')"
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
