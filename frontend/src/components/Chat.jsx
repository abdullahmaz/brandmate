import React, { useState, useRef, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ChatArea } from './ChatArea';
import { ChatInput } from './ChatInput';
import { formatDistanceToNow } from 'date-fns';
import { useChat, useSendMessage } from '../hooks/useChat';
import { MessageRole } from '../types/api';

const Chat = () => {
  const { chatId } = useParams();
  const navigate = useNavigate();
  const [optimisticMessages, setOptimisticMessages] = useState([]);
  const [localMessages, setLocalMessages] = useState([]);
  
  // Only load chat data if we have a chatId and no local messages
  const { data: chatData, isLoading: chatLoading } = useChat(chatId);
  
  // Send message mutation
  const sendMessageMutation = useSendMessage();
  
  // Convert API messages to UI format and merge with local state
  const messages = React.useMemo(() => {
    // If we have local messages (from current session), use those
    if (localMessages.length > 0) {
      return [...localMessages, ...optimisticMessages];
    }
    
    // Otherwise, use API messages
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
    
    // Merge API messages with optimistic messages, avoiding duplicates
    const allMessages = [...apiMessages];
    
    // Add optimistic messages that aren't already in API messages
    optimisticMessages.forEach(optMsg => {
      if (!apiMessages.some(apiMsg => apiMsg.id === optMsg.id)) {
        allMessages.push(optMsg);
      }
    });
    
    // Sort by timestamp to maintain order
    return allMessages.sort((a, b) => {
      const timeA = new Date(a.timestamp || 0);
      const timeB = new Date(b.timestamp || 0);
      return timeA - timeB;
    });
  }, [chatData?.messages, optimisticMessages, localMessages]);
  
  const handleSendMessage = async (message) => {
    if (!message.trim() || sendMessageMutation.isPending) return;

    // If no chatId, create a new chat first
    if (!chatId) {
      try {
        // Create new chat
        const response = await fetch('http://localhost:8000/api/chats', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            title: message.length > 50 ? message.substring(0, 50) + '...' : message
          })
        });
        
        if (!response.ok) {
          throw new Error('Failed to create chat');
        }
        
        const chatData = await response.json();
        const newChatId = chatData.chat_id;
        
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
        
        // Send the message to the new chat
        await sendMessageToChat(newChatId, message, [userMessage]);
        
      } catch (error) {
        console.error('Error creating chat:', error);
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
      await sendMessageToChat(chatId, message, messages);
    }
  };

  const sendMessageToChat = async (currentChatId, message, conversationHistory) => {
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
      const history = conversationHistory.map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      // Send message to existing chat
      const response = await fetch(`http://localhost:8000/api/chats/${currentChatId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          conversation_history: history
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to send message');
      }
      
      const responseData = await response.json();
      
      // Add assistant response to local state
      const assistantMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: responseData.message,
        message_type: responseData.tool !== 'conversation' ? responseData.tool : 'text',
        s3_url: responseData.image,
        tool: responseData.tool,
        image: responseData.image,
        timestamp: formatDistanceToNow(new Date(), { addSuffix: true })
      };
      
      setLocalMessages(prev => [...prev, assistantMessage]);
      
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
      
      // Clear error message after delay
      setTimeout(() => {
        setLocalMessages(prev => prev.filter(msg => msg.id !== errorMessage.id));
      }, 3000);
    }
  };

  const handleStop = () => {
    // Implement stop functionality
    sendMessageMutation.reset();
  };

  const isLoading = sendMessageMutation.isPending || chatLoading;

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