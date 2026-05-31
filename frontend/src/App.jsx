import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ChatSidebar } from './components/ChatSidebar';
import Chat from './components/Chat';
import { LoginDialog } from './components/LoginDialog';
import { ThemeProvider } from './components/ThemeProvider';
import { AuthProvider, useAuth } from './providers/AuthProvider';
import { QueryProvider } from './providers/QueryProvider';
import { BrandMark } from './components/BrandMark';
import { Toaster } from '@/components/ui/toaster';
import './globals.css';

function AuthedShell() {
  const { loading, loginDialogOpen } = useAuth();

  // Initial session hydration — show a quiet splash so we don't flash
  // an unauthenticated state for a frame on hard refresh.
  if (loading) {
    return (
      <div className="h-screen flex flex-col items-center justify-center gap-3 bg-background">
        <BrandMark size={36} tone="duo" />
        <p className="font-brand-italic text-sm text-muted-foreground">opening the atelier…</p>
      </div>
    );
  }

  return (
    <>
      <div className="h-screen">
        <div className="flex h-full">
          <ChatSidebar />
          <div className="flex-1 overflow-hidden bg-background">
            <Routes>
              <Route path="/" element={<Navigate to="/chat" replace />} />
              <Route path="/chat" element={<Chat />} />
              <Route path="/chat/:chatId" element={<Chat />} />
            </Routes>
          </div>
        </div>
      </div>
      {loginDialogOpen && <LoginDialog />}
    </>
  );
}

function App() {
  return (
    <QueryProvider>
      <ThemeProvider>
        <AuthProvider>
          <Router>
            <AuthedShell />
            <Toaster />
          </Router>
        </AuthProvider>
      </ThemeProvider>
    </QueryProvider>
  );
}

export default App;
