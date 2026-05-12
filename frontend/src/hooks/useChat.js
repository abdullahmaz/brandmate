import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { queryKeys } from '../types/api';
import { useAuth } from '../providers/AuthProvider';

// Get all chats — only fires when a session exists so an anon user
// never hits the API and never sees a 401 in the console.
export const useChats = (params = {}) => {
  const { session } = useAuth();
  return useQuery({
    queryKey: [...queryKeys.chats, params],
    queryFn: () => api.getChats(params),
    select: (response) => response.data,
    enabled: !!session,
  });
};

// Get specific chat with messages
export const useChat = (chatId) => {
  const { session } = useAuth();
  return useQuery({
    queryKey: queryKeys.chat(chatId),
    queryFn: () => api.getChat(chatId),
    select: (response) => response.data,
    enabled: !!chatId && !!session,
  });
};

// Send message mutation
export const useSendMessage = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ chatId, data }) => api.sendMessage(chatId, data),
    onSuccess: (response, variables) => {
      const { chatId } = variables;

      // Invalidate chat data to refresh messages
      if (chatId) {
        queryClient.invalidateQueries({ queryKey: queryKeys.chat(chatId) });
        queryClient.invalidateQueries({ queryKey: queryKeys.chats });
      }
    },
    onError: (error) => {
      console.error('Failed to send message:', error);
    },
  });
};

// Create chat mutation
export const useCreateChat = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data) => api.createChat(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.chats });
    },
    onError: (error) => {
      console.error('Failed to create chat:', error);
    },
  });
};

// Update chat title mutation
export const useUpdateChatTitle = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ chatId, title }) => api.updateChatTitle(chatId, title),
    onSuccess: (response, variables) => {
      const { chatId } = variables;
      queryClient.invalidateQueries({ queryKey: queryKeys.chat(chatId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.chats });
    },
    onError: (error) => {
      console.error('Failed to update chat title:', error);
    },
  });
};

// Delete chat mutation
export const useDeleteChat = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (chatId) => api.deleteChat(chatId),
    onSuccess: (response, chatId) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.chats });
      queryClient.removeQueries({ queryKey: queryKeys.chat(chatId) });
      queryClient.removeQueries({ queryKey: queryKeys.messages(chatId) });
    },
    onError: (error) => {
      console.error('Failed to delete chat:', error);
    },
  });
};
