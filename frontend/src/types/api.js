// API Types for Brandmate Frontend

export const MessageRole = {
  SYSTEM: 'system',
  USER: 'user',
  ASSISTANT: 'assistant'
};

export const MessageType = {
  TEXT: 'text',
  IMAGE: 'image',
  VIDEO: 'video',
  WEBSITE: 'website'
};

// Request types
export const ChatRequest = {
  message: '',
  chat_id: null,
  conversation_history: []
};

// Response types
export const ChatMessage = {
  role: '',
  content: ''
};

export const ChatResponse = {
  message: '',
  image: null,
  tool: null,
  chat_id: null,
  conversation_history: []
};

export const MessageResponse = {
  id: '',
  chat_id: '',
  role: '',
  content: '',
  message_type: '',
  s3_url: null,
  metadata: null,
  created_at: ''
};

export const Chat = {
  id: '',
  title: '',
  user_id: null,
  created_at: '',
  updated_at: ''
};

export const ChatWithMessages = {
  id: '',
  title: '',
  user_id: null,
  created_at: '',
  updated_at: '',
  messages: []
};

// Frontend message format (extends API format with UI-specific fields)
export const UIMessage = {
  id: '',
  role: '',
  content: '',
  message_type: '',
  s3_url: null,
  tool: null,
  timestamp: '',
  image: null
};

// Query key factory
export const queryKeys = {
  chats: ['chats'],
  chat: (id) => ['chats', id],
  messages: (chatId) => ['chats', chatId, 'messages'],
  health: ['health'],
  status: ['status']
};
