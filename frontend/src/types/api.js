// API Types for Brandmate Frontend

export const MessageRole = {
  SYSTEM: 'system',
  USER: 'user',
  ASSISTANT: 'assistant'
};

// Query key factory.
//
// Keys are namespaced so that invalidating the chat *list* never cascades
// into individual chat *detail* queries. Old layout had
//   chats: ['chats']
//   chat:  ['chats', id]
// which meant `invalidateQueries({queryKey: ['chats']})` refetched every
// detail query too — including the one we'd just optimistically populated,
// which produced duplicate messages.
export const queryKeys = {
  chats: ['chats', 'list'],
  chat: (id) => ['chats', 'detail', id],
  messages: (chatId) => ['chats', 'detail', chatId, 'messages']
};
