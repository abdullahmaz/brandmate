import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
apiClient.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const api = {
  // Chat management
  createChat: (data) => apiClient.post('/api/chats', data),
  getChats: (params = {}) => apiClient.get('/api/chats', { params }),
  getChat: (chatId) => apiClient.get(`/api/chats/${chatId}`),
  updateChatTitle: (chatId, title) => apiClient.put(`/api/chats/${chatId}/title`, null, { 
    params: { title } 
  }),
  deleteChat: (chatId) => apiClient.delete(`/api/chats/${chatId}`),
  
  // Message endpoints
  sendMessage: (chatId, data, signal) => apiClient.post(`/api/chats/${chatId}/messages`, data, { signal }),
  getMessages: (chatId, params = {}) => apiClient.get(`/api/chats/${chatId}/messages`, { params }),
  
  // Health check
  getHealth: () => apiClient.get('/health'),
};

export default apiClient;
