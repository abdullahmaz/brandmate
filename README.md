# Brandmate: AI-Powered Brand Automation for Eastern Clothing Brands

An intelligent AI platform that automates end-to-end brand marketing for Eastern clothing brands using advanced LLM orchestration and multimodal AI tools. Brandmate understands natural language requests and automatically generates marketing assets, visual content, and brand materials tailored specifically for Eastern clothing brands.

## 🌟 Features

- **🤖 Intelligent Chat Interface**: Claude-like conversational AI for natural brand asset requests
- **🧠 LLM Orchestrator**: Uses Llama 3.2 3B Instruct for intelligent reasoning and tool calling
- **🎨 Image Generation**: Creates stunning Eastern clothing marketing visuals using Stable Diffusion
- **📝 Text Generation**: Generates marketing copy, captions, and brand descriptions
- **🎬 Video Generation**: Creates promotional videos and social media content
- **🌐 Website Generation**: Builds landing pages and web content
- **🎯 Brand Consistency**: Specialized for Eastern clothing brands and seasonal collections
- **💎 Modern UI**: Built with React, TailwindCSS, and ShadCN components

## 🏗️ Project Structure

```
brandmate/
├── frontend/              # React + Vite + ShadCN UI frontend
│   ├── src/
│   │   ├── components/    # Reusable UI components
│   │   │   ├── ui/        # ShadCN UI components
│   │   │   ├── Chat.jsx   # Main chat interface
│   │   │   ├── ChatArea.jsx # Message display area
│   │   │   ├── ChatInput.jsx # Message input component
│   │   │   └── ChatMessage.jsx # Individual message component
│   │   ├── lib/           # Utility functions
│   │   └── App.jsx        # Main application component
│   ├── package.json
│   └── README.md
├── backend/               # FastAPI backend with AI orchestration
│   ├── main.py           # FastAPI server and API endpoints
│   ├── llm_orchestrator.py # LLM orchestration and tool calling
│   ├── image_generator.py # Image generation using Stable Diffusion
│   ├── install_models.py # Model installation scripts
│   ├── requirements.txt  # Python dependencies
│   └── README.md
├── start_dev.bat         # Development startup script (Windows)
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- **Node.js 18+** (for frontend development)
- **Python 3.8+** (for backend)
- **Git** (for version control)
- **8GB+ RAM** (16GB recommended for optimal performance)
- **10GB+ storage** (for model downloads)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd brandmate
   ```

2. **Setup Backend:**
   ```bash
   cd backend
   pip install -r requirements.txt
   cp env_example.txt .env
   # Edit .env with your configuration
   python install_models.py  # Download required models
   ```

3. **Setup Frontend:**
   ```bash
   cd frontend
   npm install
   ```

4. **Start Development Servers:**
   ```bash
   # Option 1: Use the batch script (Windows)
   start_dev.bat
   
   # Option 2: Manual start
   # Terminal 1 - Backend
   cd backend && python main.py
   
   # Terminal 2 - Frontend  
   cd frontend && npm run dev
   ```

5. **Access the Application:**
   - **Frontend**: http://localhost:5173
   - **Backend API**: http://localhost:8000
   - **API Documentation**: http://localhost:8000/docs

## 💡 Usage

### Getting Started

1. Open the frontend in your browser at `http://localhost:5173`
2. Start a conversation by describing what you want to create
3. The LLM orchestrator will analyze your request and determine the best tools to use
4. Generated content will appear in the chat interface
5. Download or copy the generated assets as needed

### Example Prompts

**Image Generation:**
- "Create a poster for my summer lawn collection"
- "Generate a marketing image for my winter khaddar line"
- "Design a banner for my Eastern clothing brand launch"
- "Make a social media post for my Eid collection"

**Text Generation:**
- "Write a product description for my new shalwar kameez line"
- "Create Instagram captions for my wedding collection"
- "Generate marketing copy for my brand's website"

**Video Generation:**
- "Create a promotional video for my new collection"
- "Make a TikTok-style reel showcasing my Eastern wear"

**Website Generation:**
- "Build a landing page for my clothing brand"
- "Create a product showcase page for my collection"

## 🛠️ Technology Stack

### Frontend
- **React 18** - Modern UI library
- **Vite** - Fast build tool and dev server
- **TailwindCSS** - Utility-first CSS framework
- **ShadCN UI** - High-quality component library
- **Lucide React** - Beautiful icon library
- **date-fns** - Date manipulation utilities

### Backend
- **FastAPI** - Modern, fast web framework for APIs
- **Llama 3.2 3B Instruct** - Large language model for orchestration
- **Stable Diffusion v1.5** - Image generation model
- **Hugging Face Transformers** - Model loading and inference
- **Pydantic** - Data validation and settings management
- **Uvicorn** - ASGI server for FastAPI

## 🔧 Development

### Frontend Development
```bash
cd frontend
npm run dev          # Start development server
npm run build        # Build for production
npm run preview      # Preview production build
```

### Backend Development
```bash
cd backend
python main.py       # Start development server
python -m uvicorn main:app --reload  # Alternative with auto-reload
```

### API Development
- Interactive API documentation: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc
- OpenAPI schema: http://localhost:8000/openapi.json

## 📊 System Requirements

### Minimum Requirements
- **RAM**: 8GB
- **Storage**: 10GB (for models)
- **CPU**: 4+ cores
- **Python**: 3.8+
- **Node.js**: 18+

### Recommended Requirements
- **RAM**: 16GB+
- **Storage**: 20GB+ SSD
- **GPU**: NVIDIA with 8GB+ VRAM
- **CPU**: 8+ cores

## 🎯 AI Capabilities

### LLM Orchestrator
- **Model**: Llama 3.2 3B Instruct (3B parameters)
- **Capabilities**: Natural language understanding, tool calling, reasoning
- **Features**: Context-aware responses, intelligent tool selection

### Image Generation
- **Model**: Stable Diffusion v1.5
- **Specialization**: Eastern clothing, traditional wear, seasonal collections
- **Output**: High-quality PNG images with base64 encoding

### Tool Calling System
The LLM can intelligently call these tools based on user requests:
- `image_generation` - Create visual content
- `text_generation` - Generate marketing copy
- `video_generation` - Create promotional videos
- `website_generation` - Build web content

## 🚀 Deployment

### Production Build
```bash
# Frontend
cd frontend
npm run build

# Backend
cd backend
pip install -r requirements.txt
python main.py
```

### Environment Variables
Create a `.env` file in the backend directory:
```env
HUGGINGFACE_API_TOKEN=your_token_here
MODEL_CACHE_DIR=./models
DEBUG=False
```

## 👥 Project Team

- **Abdullah Mazhar** (22i-0622) - Backend Development, Dashboard, Brand Consistency
- **Katrina Bodani** (22i-0545) - Image/Video/Text Models, Website Mockups
- **Haider Niaz** (22i-0481) - Image/Video/Text Models, Billboard Module

## 📄 License

This project is part of the Final Year Project at FAST NUCES, Islamabad.

## 🔮 Roadmap

### Completed ✅
- [x] Basic chat interface with React and ShadCN UI
- [x] FastAPI backend with LLM orchestration
- [x] Image generation using Stable Diffusion
- [x] Tool calling system for AI capabilities
- [x] Base64 image display in frontend

### In Progress 🚧
- [ ] Enhanced image generation with Eastern clothing specialization
- [ ] Text generation capabilities
- [ ] Video generation features
- [ ] Website generation module

### Planned 📋
- [ ] Brand consistency validation
- [ ] Advanced prompt engineering for Eastern clothing
- [ ] Batch processing capabilities
- [ ] User authentication and project management
- [ ] Cloud deployment and scaling
- [ ] Mobile-responsive design improvements
- [ ] Real-time collaboration features

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the API documentation at `/docs`

## 🙏 Acknowledgments

- OpenAI for the GPT-OSS model
- Hugging Face for the model hosting and transformers library
- Stability AI for Stable Diffusion
- The React and FastAPI communities
- ShadCN for the beautiful UI components