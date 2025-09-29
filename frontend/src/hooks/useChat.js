import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { queryKeys } from '../types/api';

// Get all chats
export const useChats = (params = {}) => {
  return useQuery({
    queryKey: [...queryKeys.chats, params],
    queryFn: () => api.getChats(params),
    select: (response) => response.data,
  });
};

// Get specific chat with messages
export const useChat = (chatId) => {
  return useQuery({
    queryKey: queryKeys.chat(chatId),
    queryFn: () => api.getChat(chatId),
    select: (response) => response.data,
    enabled: !!chatId,
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
    onSuccess: (response) => {
      // Invalidate chats list to show the new chat
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
      
      // Invalidate chat data
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
      // Invalidate chats list to remove the deleted chat
      queryClient.invalidateQueries({ queryKey: queryKeys.chats });
      
      // Remove the specific chat from cache
      queryClient.removeQueries({ queryKey: queryKeys.chat(chatId) });
      queryClient.removeQueries({ queryKey: queryKeys.messages(chatId) });
    },
    onError: (error) => {
      console.error('Failed to delete chat:', error);
    },
  });
};