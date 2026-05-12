import axios from 'axios';
import { supabase } from '../lib/supabaseClient';

export const API_BASE_URL = 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ── Request interceptor ─────────────────────────────────────────────
// Attach the current Supabase access token (if any) to every API call.
// We pull from supabase.auth.getSession() rather than from a closure
// over the AuthProvider state so this works even if a request is fired
// before/outside the React tree (e.g. video conversion fetches).
apiClient.interceptors.request.use(
  async (config) => {
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (err) {
      // Don't block the request — the backend will respond 401 if it
      // genuinely required auth and we'll handle it in the response
      // interceptor below.
      console.warn('[api] Failed to read Supabase session for auth header', err);
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ── Response interceptor ────────────────────────────────────────────
// On 401, force a sign-out so the LoginDialog re-opens. Avoids the app
// silently retrying with a stale token forever.
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error.response?.status;
    if (status === 401) {
      try {
        await supabase.auth.signOut();
      } catch { /* noop */ }
    }
    return Promise.reject(error);
  },
);

export const api = {
  // Chat management
  createChat: (data) => apiClient.post('/api/chats', data),
  getChats: (params = {}) => apiClient.get('/api/chats', { params }),
  getChat: (chatId) => apiClient.get(`/api/chats/${chatId}`),
  updateChatTitle: (chatId, title) => apiClient.put(`/api/chats/${chatId}/title`, null, {
    params: { title },
  }),
  deleteChat: (chatId) => apiClient.delete(`/api/chats/${chatId}`),

  // Message endpoints
  sendMessage: (chatId, data, signal) => apiClient.post(`/api/chats/${chatId}/messages`, data, { signal }),
  getMessages: (chatId, params = {}) => apiClient.get(`/api/chats/${chatId}/messages`, { params }),

  // Health check
  getHealth: () => apiClient.get('/health'),
};

export default apiClient;
