# Brandmate frontend

React 19 chat UI for the Brandmate platform. Built with Vite (rolldown), TailwindCSS,
ShadCN, React Query, and Supabase auth.

## Quick start

```bash
cp .env.example .env          # add your Supabase URL + anon key
npm install
npm run dev                   # http://localhost:5173
```

The backend should be running at `http://localhost:8000` — see [`../backend/README.md`](../backend/README.md).

## Environment

```env
VITE_SUPABASE_URL=https://<your-project>.supabase.co
VITE_SUPABASE_ANON_KEY=<your-anon-key>
```

Supabase is used for authentication. The frontend grabs the user's JWT and attaches it as
a `Bearer` token on every backend call; the backend validates against the same project.

## Scripts

```bash
npm run dev        # Vite dev server with HMR
npm run build      # Production build to dist/
npm run preview    # Preview the production build locally
npm run lint       # ESLint
```

## Stack

- **React 19** with **React Router 7** for routing
- **Vite** (replaced by `rolldown-vite` via npm override for faster builds)
- **TailwindCSS 3** + **ShadCN UI** + `tailwindcss-animate`
- **React Query 5** for server state, caching, and request dedup
- **Axios** for HTTP with a request interceptor that injects the Supabase JWT
- **react-markdown** + `@tailwindcss/typography` for rendering generated copy
- **lucide-react** for icons, **date-fns** for relative timestamps

## Structure

```
src/
├── App.jsx                   AuthProvider → Router → ChatSidebar + Chat
├── components/
│   ├── Chat.jsx              Main chat view, hooks into useChat
│   ├── ChatSidebar.jsx       Chat history list, new-chat button
│   ├── ChatArea.jsx          Scrollable message list with auto-scroll
│   ├── ChatInput.jsx         Auto-resizing input, image upload, quality selector
│   ├── ChatMessage.jsx       Renders text / image / video / HTML messages
│   ├── HoverActions.jsx      Copy / download / convert-video actions
│   ├── LoginDialog.jsx       Supabase email + OAuth login modal
│   ├── BrandMark.jsx         Logo / wordmark
│   ├── ThemeProvider.jsx     Light/dark theme context
│   └── ui/                   ShadCN primitives
├── hooks/
│   ├── useChat.js            Chat state, send/abort, message normalization
│   └── use-toast.js          Toast helper bound to <Toaster />
├── providers/
│   ├── AuthProvider.jsx      Supabase session, sign-in/out, login modal control
│   └── QueryProvider.jsx     React Query client
├── services/
│   └── api.js                Axios client + endpoint methods
├── lib/
│   ├── supabaseClient.js     Supabase SDK init
│   └── utils.js              `cn()` for class merging
├── constants/
│   ├── toolTypes.js          Tool name → display metadata
│   └── loadingWords.js       Rotating loading copy
└── types/api.js              JSDoc-style typedefs for API responses
```

## API client

`services/api.js` exposes a small typed client over the backend:

| Method                              | Endpoint                                |
| ----------------------------------- | --------------------------------------- |
| `api.createChat(data)`              | `POST   /api/chats`                     |
| `api.getChats({ limit })`           | `GET    /api/chats`                     |
| `api.getChat(chatId)`               | `GET    /api/chats/{chatId}`            |
| `api.updateChatTitle(chatId, t)`    | `PUT    /api/chats/{chatId}/title`      |
| `api.deleteChat(chatId)`            | `DELETE /api/chats/{chatId}`            |
| `api.sendMessage(chatId, d, sig)`   | `POST   /api/chats/{chatId}/messages`   |
| `api.getMessages(chatId, params)`   | `GET    /api/chats/{chatId}/messages`   |

The request interceptor reads `supabase.auth.getSession()` on every call — so requests
fired outside the React tree still carry the right token. A 401 response forces a sign-out,
which surfaces the login dialog.

Messages support extra fields the backend understands:

- `image_base64` — attach an image to drive image-to-video
- `current_city`, `current_lat`, `current_lon` — used by the billboard "near me" flow
- `quality_mode` — `"speed" | "balanced" | "quality"` for the video pipeline

## Build & deploy

```bash
npm run build       # outputs to dist/
npm run preview     # smoke-test the production bundle
```

The dev API base URL (`http://localhost:8000`) is hardcoded in `services/api.js`. For
production, swap it to read from `import.meta.env.VITE_API_URL` and host the bundle on any
static target (Vercel, Netlify, S3 + CloudFront, nginx).
