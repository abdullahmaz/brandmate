# Brandmate Frontend

Modern React frontend for the Brandmate AI-powered brand automation platform. Built with Vite, TailwindCSS, and ShadCN UI components for a beautiful, responsive chat interface.

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- npm or yarn
- Backend server running on port 8000

### Installation

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Start development server:**
   ```bash
   npm run dev
   ```

3. **Access the application:**
   Open [http://localhost:5173](http://localhost:5173) in your browser

## 🏗️ Project Structure

```
frontend/
├── src/
│   ├── components/           # React components
│   │   ├── ui/              # ShadCN UI components
│   │   │   ├── avatar.jsx   # User/AI avatar component
│   │   │   ├── button.jsx   # Button component
│   │   │   ├── card.jsx     # Card container component
│   │   │   ├── input.jsx    # Input field component
│   │   │   ├── scroll-area.jsx # Scrollable area component
│   │   │   ├── separator.jsx # Visual separator component
│   │   │   └── textarea.jsx # Textarea component
│   │   ├── Chat.jsx         # Main chat interface component
│   │   ├── ChatArea.jsx     # Message display area
│   │   ├── ChatInput.jsx    # Message input component
│   │   ├── ChatMessage.jsx  # Individual message component
│   │   ├── ChatSidebar.jsx  # Sidebar for chat history
│   │   └── ThemeProvider.jsx # Theme context provider
│   ├── lib/
│   │   └── utils.js         # Utility functions
│   ├── App.jsx              # Main application component
│   ├── App.css              # Application styles
│   ├── main.jsx             # Application entry point
│   ├── index.css            # Global styles
│   └── globals.css          # Global CSS variables
├── public/
│   └── vite.svg             # Vite logo
├── components.json           # ShadCN UI configuration
├── package.json             # Dependencies and scripts
├── tailwind.config.js       # TailwindCSS configuration
├── postcss.config.js        # PostCSS configuration
├── vite.config.js           # Vite configuration
└── README.md
```

## 🎨 Components

### Core Components

#### `Chat.jsx`
Main chat interface component that manages:
- Message state and history
- API communication with backend
- Loading states and error handling
- Message formatting and timestamps

**Props:** None (manages internal state)

**Key Features:**
- Real-time message updates
- Error handling and fallbacks
- Timestamp formatting with `date-fns`
- Loading indicators

#### `ChatArea.jsx`
Message display area component that:
- Renders message list
- Handles auto-scrolling
- Shows loading states
- Manages empty states

**Props:**
- `messages` (Array): List of message objects
- `isLoading` (Boolean): Loading state indicator

**Key Features:**
- Auto-scroll to bottom on new messages
- Smooth scrolling animations
- Empty state with welcome message
- Loading animation with dots

#### `ChatMessage.jsx`
Individual message component that displays:
- User and assistant messages
- Generated images
- Tool usage indicators
- Timestamps

**Props:**
- `role` (String): 'user' or 'assistant'
- `content` (String): Message text content
- `timestamp` (String): Formatted timestamp
- `image` (String): Base64 image data (optional)
- `tool` (String): Tool used for generation (optional)

**Key Features:**
- Different styling for user vs assistant messages
- Image display with proper sizing
- Tool usage indicators
- Responsive design

#### `ChatInput.jsx`
Message input component that handles:
- Text input and submission
- Loading states
- Stop functionality
- Keyboard shortcuts

**Props:**
- `onSendMessage` (Function): Callback for sending messages
- `isLoading` (Boolean): Loading state
- `onStop` (Function): Callback for stopping generation

**Key Features:**
- Auto-resize textarea
- Enter to send, Shift+Enter for new line
- Loading state with disabled input
- Stop button during generation

### UI Components (ShadCN)

#### `Avatar.jsx`
User and AI avatar component with fallback initials.

#### `Button.jsx`
Versatile button component with multiple variants and sizes.

#### `Card.jsx`
Container component for grouping related content.

#### `Input.jsx`
Form input component with consistent styling.

#### `ScrollArea.jsx`
Custom scrollable area with smooth scrolling.

#### `Separator.jsx`
Visual separator component for dividing content.

#### `Textarea.jsx`
Multi-line text input component.

## 🎯 Features

### Chat Interface
- **Real-time Messaging**: Instant message updates and responses
- **Image Display**: Shows generated images inline with messages
- **Loading States**: Visual feedback during AI processing
- **Error Handling**: Graceful error messages and fallbacks
- **Responsive Design**: Works on desktop and mobile devices

### User Experience
- **Auto-scroll**: Automatically scrolls to new messages
- **Keyboard Shortcuts**: Enter to send, Shift+Enter for new line
- **Timestamps**: Relative time display (e.g., "2 minutes ago")
- **Tool Indicators**: Shows which AI tool was used
- **Empty States**: Welcome message when no conversations exist

### Styling
- **Dark/Light Theme**: Automatic theme detection
- **TailwindCSS**: Utility-first CSS framework
- **ShadCN UI**: High-quality component library
- **Responsive**: Mobile-first responsive design
- **Animations**: Smooth transitions and loading states

## 🛠️ Development

### Available Scripts

```bash
npm run dev          # Start development server
npm run build        # Build for production
npm run preview      # Preview production build
npm run lint         # Run ESLint
```

### Development Server

The development server runs on `http://localhost:5173` with:
- Hot Module Replacement (HMR)
- Fast refresh for React components
- Automatic browser refresh on changes
- Source maps for debugging

### Building for Production

```bash
npm run build
```

This creates an optimized production build in the `dist/` directory with:
- Minified JavaScript and CSS
- Optimized assets
- Tree-shaking for smaller bundle size
- Source maps for debugging

## ⚙️ Configuration

### Vite Configuration (`vite.config.js`)

```javascript
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
})
```

### TailwindCSS Configuration (`tailwind.config.js`)

```javascript
module.exports = {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        // ... more colors
      }
    }
  },
  plugins: [require("tailwindcss-animate")]
}
```

### ShadCN UI Configuration (`components.json`)

```json
{
  "style": "default",
  "rsc": false,
  "tsx": false,
  "tailwind": {
    "config": "tailwind.config.js",
    "css": "src/index.css",
    "baseColor": "slate",
    "cssVariables": true
  },
  "aliases": {
    "components": "src/components",
    "utils": "src/lib/utils"
  }
}
```

## 🎨 Styling

### CSS Architecture
- **Global Styles**: `index.css` and `globals.css`
- **Component Styles**: Inline with TailwindCSS classes
- **CSS Variables**: For consistent theming
- **Responsive Design**: Mobile-first approach

### Theme System
- **CSS Variables**: Defined in `globals.css`
- **Dark/Light Mode**: Automatic detection
- **Color Palette**: Consistent color scheme
- **Typography**: Inter font family

### Component Styling
- **Utility Classes**: TailwindCSS for styling
- **Component Variants**: ShadCN UI variants
- **Responsive**: Mobile-first responsive design
- **Animations**: Smooth transitions and hover effects

## 🔌 API Integration

### Backend Communication
- **Base URL**: `http://localhost:8000`
- **Endpoints**: `/api/chat` for main communication
- **Error Handling**: Graceful error messages
- **Loading States**: Visual feedback during requests

### Message Format
```javascript
// Request
{
  "message": "Create a poster for my brand"
}

// Response
{
  "message": "I've generated an image for your request...",
  "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "tool": "image_generation"
}
```

## 📱 Responsive Design

### Breakpoints
- **Mobile**: < 640px
- **Tablet**: 640px - 1024px
- **Desktop**: > 1024px

### Mobile Features
- Touch-friendly interface
- Responsive message bubbles
- Optimized image display
- Mobile keyboard handling

## 🚀 Performance

### Optimization Features
- **Code Splitting**: Automatic code splitting with Vite
- **Tree Shaking**: Removes unused code
- **Image Optimization**: Efficient image handling
- **Lazy Loading**: Components load as needed

### Bundle Analysis
```bash
npm run build
# Check dist/ directory for optimized files
```

## 🧪 Testing

### Component Testing
```bash
# Install testing dependencies
npm install --save-dev @testing-library/react @testing-library/jest-dom

# Run tests
npm test
```

### Manual Testing
- Test all user interactions
- Verify responsive design
- Check error handling
- Test image display

## 🐛 Debugging

### Development Tools
- **React DevTools**: Browser extension
- **Vite DevTools**: Built-in debugging
- **Console Logging**: Debug information
- **Source Maps**: For debugging production builds

### Common Issues
- **CORS Errors**: Check backend CORS configuration
- **Image Display**: Verify base64 format
- **Styling Issues**: Check TailwindCSS classes
- **API Errors**: Check network tab in dev tools

## 🚀 Deployment

### Production Build
```bash
npm run build
```

### Deployment Options
- **Static Hosting**: Vercel, Netlify, GitHub Pages
- **CDN**: CloudFlare, AWS CloudFront
- **Server**: Nginx, Apache

### Environment Variables
```bash
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=Brandmate
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Code Style
- Use Prettier for formatting
- Follow React best practices
- Use meaningful component names
- Add comments for complex logic

## 📞 Support

For issues and questions:
- Check the browser console for errors
- Review the component documentation
- Create an issue in the repository
- Contact the development team

## 📄 License

This project is part of the Final Year Project at FAST NUCES, Islamabad.

## 🙏 Acknowledgments

- **Vite** for the fast build tool
- **React** for the UI library
- **TailwindCSS** for the styling framework
- **ShadCN UI** for the component library
- **date-fns** for date utilities
