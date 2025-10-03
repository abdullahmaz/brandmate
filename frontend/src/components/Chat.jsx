import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ChatArea } from './ChatArea';
import { ChatInput } from './ChatInput';
import { formatDistanceToNow } from 'date-fns';
import { useChat, useCreateChat } from '../hooks/useChat';
import { api } from '../services/api';
import { queryKeys } from '../types/api';

const Chat = () => {
  const { chatId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [localMessages, setLocalMessages] = useState([]);
  
  // Only load chat data if we have a chatId and no local messages
  const { data: chatData, isLoading: chatLoading } = useChat(chatId);
  
  // Send message mutation with custom onSuccess handler
  const sendMessageMutation = useMutation({
    mutationFn: ({ chatId, data }) => api.sendMessage(chatId, data),
    onSuccess: (response, variables) => {
      const { chatId } = variables;
      
      // Clear local messages since they'll be replaced by fresh API data
      setLocalMessages([]);
      
      // Invalidate chat data to refresh messages
      if (chatId) {
        queryClient.invalidateQueries({ queryKey: queryKeys.chat(chatId) });
      }
    },
    onError: (error) => {
      console.error('Failed to send message:', error);
      
      const errorMessage = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, there was an error processing your request. Please try again.',
        message_type: 'text',
        timestamp: formatDistanceToNow(new Date(), { addSuffix: true })
      };
      
      setLocalMessages(prev => [...prev, errorMessage]);
    },
  });
  
  // Create chat mutation
  const createChatMutation = useCreateChat();
  
  // Convert API messages to UI format and merge with local state
  const messages = React.useMemo(() => {
    // Convert API messages to UI format
    const apiMessages = chatData?.messages ? chatData.messages.map(msg => ({
      id: msg.id,
      role: msg.role,
      content: msg.content,
      message_type: msg.message_type,
      s3_url: msg.s3_url,
      tool: msg.message_type !== 'text' ? msg.message_type : null,
      image: msg.s3_url || null,
      timestamp: formatDistanceToNow(new Date(msg.created_at), { addSuffix: true })
    })) : [];
    
    if (localMessages.length > 0 && (sendMessageMutation.isPending || createChatMutation.isPending)) {
      const filteredLocalMessages = localMessages.filter(localMsg => 
        !apiMessages.some(apiMsg => 
          apiMsg.content === localMsg.content && 
          apiMsg.role === localMsg.role
        )
      );
      
      return [...apiMessages, ...filteredLocalMessages];
    }
    
    return apiMessages;
  }, [chatData?.messages, localMessages, sendMessageMutation.isPending, createChatMutation.isPending]);
  
  const handleSendMessage = async (message) => {
    if (!message.trim() || sendMessageMutation.isPending || createChatMutation.isPending) return;

    // If no chatId, create a new chat first
    if (!chatId) {
      try {
        // Create new chat using the mutation hook
        const chatData = await createChatMutation.mutateAsync({
          title: message.length > 50 ? message.substring(0, 50) + '...' : message
        });
        
        const newChatId = chatData.data.chat_id;
        
        // Navigate to the new chat
        navigate(`/chat/${newChatId}`);
        
        // Add user message to local state
        const userMessage = {
          id: `user-${Date.now()}`,
          role: 'user',
          content: message,
          message_type: 'text',
          timestamp: formatDistanceToNow(new Date(), { addSuffix: true })
        };
        
        setLocalMessages([userMessage]);
        
        // Send the message to the new chat using the mutation
        sendMessageMutation.mutate({
          chatId: newChatId,
          data: {
            message,
            conversation_history: [userMessage].map(msg => ({
              role: msg.role,
              content: msg.content
            }))
          }
        });
        
      } catch (error) {
        console.error('Error creating chat or sending message:', error);
        // Add error message to local state
        const errorMessage = {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: 'Sorry, there was an error creating a new chat. Please try again.',
          message_type: 'text',
          timestamp: formatDistanceToNow(new Date(), { addSuffix: true })
        };
        
        setLocalMessages(prev => [...prev, errorMessage]);
      }
    } else {
      // Chat exists, send message normally
      try {
        // Add user message to local state immediately
        const userMessage = {
          id: `user-${Date.now()}`,
          role: 'user',
          content: message,
          message_type: 'text',
          timestamp: formatDistanceToNow(new Date(), { addSuffix: true })
        };
        
        setLocalMessages(prev => [...prev, userMessage]);

        // Prepare conversation history for the API
        const history = messages.map(msg => ({
          role: msg.role,
          content: msg.content
        }));

        // Send message using the mutation
        sendMessageMutation.mutate({
          chatId: chatId,
          data: {
            message,
            conversation_history: history
          }
        });
        
      } catch (error) {
        console.error('Error sending message:', error);
        
        // Add error message to local state
        const errorMessage = {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: 'Sorry, there was an error processing your request. Please try again.',
          message_type: 'text',
          timestamp: formatDistanceToNow(new Date(), { addSuffix: true })
        };
        
        setLocalMessages(prev => [...prev, errorMessage]);
      }
    }
  };

  const handleStop = () => {
    sendMessageMutation.reset();
  };

  const isLoading = sendMessageMutation.isPending || createChatMutation.isPending || chatLoading;

  // Show welcome message when no chat is selected
  if (!chatId) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center max-w-md mx-auto px-6">
            <h1 className="text-2xl font-bold text-foreground mb-4">Welcome to Brandmate</h1>
            <p className="text-muted-foreground mb-6">
              Start a new conversation by typing a message below.
            </p>
          </div>
        </div>
        <ChatInput 
          onSendMessage={handleSendMessage} 
          isLoading={isLoading}
          onStop={handleStop}
          placeholder="Type your message to start a new conversation..."
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-hidden flex flex-col">
        <ChatArea messages={messages} isLoading={isLoading} />
      </div>
      <ChatInput 
        onSendMessage={handleSendMessage} 
        isLoading={isLoading}
        onStop={handleStop}
      />
    </div>
  );
};

export default Chat;