import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ChatSidebar } from './components/ChatSidebar';
import Chat from './components/Chat';
import { ThemeProvider } from './components/ThemeProvider';
import { QueryProvider } from './providers/QueryProvider';
import './globals.css';

function App() {
  return (
    <QueryProvider>
      <ThemeProvider>
        <Router>
          <div className="min-h-screen px-4 py-6 md:px-6">
            <div className="mx-auto flex h-[calc(100vh-48px)] max-w-[1400px] gap-6">
              <ChatSidebar />

              {/* Main Content */}
              <div className="flex-1 overflow-hidden rounded-2xl border border-border/70 bg-card/80 shadow-2xl shadow-black/5 backdrop-blur-lg">
                <Routes>
                  <Route path="/" element={<Navigate to="/chat" replace />} />
                  <Route path="/chat" element={<Chat />} />
                  <Route path="/chat/:chatId" element={<Chat />} />
                </Routes>
              </div>
            </div>
          </div>
        </Router>
      </ThemeProvider>
    </QueryProvider>
  );
}

export default App;