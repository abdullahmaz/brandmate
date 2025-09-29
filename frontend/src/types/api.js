// API Types for Brandmate Frontend

export const MessageRole = {
  SYSTEM: 'system',
  USER: 'user',
  ASSISTANT: 'assistant'
};

// Query key factory
export const queryKeys = {
  chats: ['chats'],
  chat: (id) => ['chats', id],
  messages: (chatId) => ['chats', chatId, 'messages']
};
