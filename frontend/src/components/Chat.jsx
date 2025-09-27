import React, { useState, useRef, useEffect } from 'react';
import { ChatArea } from './ChatArea';
import { ChatInput } from './ChatInput';
import { formatDistanceToNow } from 'date-fns';

const Chat = () => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  
  const handleSendMessage = async (message) => {
    if (!message.trim() || isLoading) return;

    const userMessage = { 
      id: Date.now().toString(), 
      role: 'user', 
      content: message,
      timestamp: formatDistanceToNow(new Date(), { addSuffix: true })
    };
    
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message }),
      });

      const data = await response.json();
      
      setMessages(prev => [...prev, { 
        id: (Date.now() + 1).toString(),
        role: 'assistant', 
        content: data.message,
        image: data.image || null,
        tool: data.tool || null,
        timestamp: formatDistanceToNow(new Date(), { addSuffix: true })
      }]);
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, { 
        id: (Date.now() + 1).toString(),
        role: 'assistant', 
        content: 'Sorry, there was an error processing your request. Please make sure the backend is running.',
        image: null,
        tool: 'error',
        timestamp: formatDistanceToNow(new Date(), { addSuffix: true })
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStop = () => {
    // Implement stop functionality
    setIsLoading(false);
  };

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