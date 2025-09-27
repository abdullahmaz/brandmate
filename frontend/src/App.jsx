import React, { useState } from 'react';
import Chat from './components/Chat';
import { ChatSidebar } from './components/ChatSidebar';
import { ThemeProvider } from './components/ThemeProvider';
import './globals.css';

function App() {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [selectedConversationId, setSelectedConversationId] = useState('1');
  
  const toggleSidebar = () => {
    setIsSidebarCollapsed(prev => !prev);
  };
  
  const handleSelectConversation = (id) => {
    setSelectedConversationId(id);
  };
  
  const handleNewConversation = () => {
    // In a real app, you would create a new conversation here
    console.log('Creating new conversation');
  };
  
  return (
    <ThemeProvider>
      <div className="flex h-screen">
        <ChatSidebar 
          isCollapsed={isSidebarCollapsed}
          onToggle={toggleSidebar}
          selectedConversationId={selectedConversationId}
          onSelectConversation={handleSelectConversation}
          onNewConversation={handleNewConversation}
        />
        
        {/* Main Content */}
        <div className="flex-1 bg-background">
          <Chat />
        </div>
      </div>
    </ThemeProvider>
  );
}

export default App;
