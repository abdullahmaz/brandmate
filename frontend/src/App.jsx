import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ChatSidebar } from './components/ChatSidebar';
import Chat from './components/Chat';
import { ThemeProvider } from './components/ThemeProvider';
import { QueryProvider } from './providers/QueryProvider';
import { Toaster } from '@/components/ui/toaster';
import './globals.css';

function App() {
  return (
    <QueryProvider>
      <ThemeProvider>
        <Router>
          <div className="h-screen">
            <div className="flex h-full">
              <ChatSidebar />

              {/* Main Content */}
              <div className="flex-1 overflow-hidden bg-background">
                <Routes>
                  <Route path="/" element={<Navigate to="/chat" replace />} />
                  <Route path="/chat" element={<Chat />} />
                  <Route path="/chat/:chatId" element={<Chat />} />
                </Routes>
              </div>
            </div>
          </div>
          <Toaster />
        </Router>
      </ThemeProvider>
    </QueryProvider>
  );
}

export default App;