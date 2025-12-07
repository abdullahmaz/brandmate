import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Button } from './ui/button';
import {
  PlusIcon,
  MessageSquare,
  PanelLeftClose,
  Settings,
  Loader2,
  Trash2,
  Sun,
  Moon,
} from 'lucide-react';
import { useChats, useDeleteChat } from '../hooks/useChat';
import { formatDistanceToNow } from 'date-fns';
import { useTheme } from './ThemeProvider';

/**
 * Chat sidebar component that shows conversations list
 */
export function ChatSidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();

  const { data: chats, isLoading } = useChats();
  const deleteChatMutation = useDeleteChat();
  const [deletingChatId, setDeletingChatId] = useState(null);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const onToggle = () => setIsCollapsed((prev) => !prev);

  
  const selectedConversationId = location.pathname.split('/').pop();
  
  const handleNewConversation = () => {
    navigate('/chat');
  };
  
  const handleSelectConversation = (conversationId) => {
    navigate(`/chat/${conversationId}`);
  };

  const handleDeleteClick = async (e, conversationId) => {
    e.stopPropagation(); // Prevent triggering the conversation selection
    
    setDeletingChatId(conversationId);
    
    try {
      await deleteChatMutation.mutateAsync(conversationId);
      
      // If we're currently viewing the deleted chat, navigate to home
      if (selectedConversationId === conversationId) {
        navigate('/chat');
      }
    } catch (error) {
      console.error('Failed to delete chat:', error);
      // You could add a toast notification here
    } finally {
      setDeletingChatId(null);
    }
  };

  if (isCollapsed) {
    return (
      <div className="w-16 bg-sidebar border-r border-sidebar-border flex flex-col items-center py-4 gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggle}
          className="text-sidebar-foreground hover:bg-sidebar-accent"
        >
          <PanelLeftClose className="h-5 w-5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={handleNewConversation}
          className="text-sidebar-foreground hover:bg-sidebar-accent"
        >
          <PlusIcon className="h-5 w-5" />
        </Button>
        <div className="flex-1" />
        <Button
          variant="ghost"
          size="icon"
          className="text-sidebar-foreground hover:bg-sidebar-accent"
        >
          <Settings className="h-5 w-5" />
        </Button>
      </div>
    );
  }

  return (
    <div className="w-80 bg-sidebar border-r border-sidebar-border flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-sidebar-border flex-shrink-0">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sidebar-foreground font-bold">Brandmate</h3>
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggle}
          >
            <PanelLeftClose className="h-5 w-5" />
          </Button>
        </div>
        <Button 
          onClick={handleNewConversation}
          className="w-full bg-sidebar-primary text-sidebar-primary-foreground hover:bg-sidebar-primary/90"
        >
          <PlusIcon className="h-4 w-4 mr-2" />
          New Conversation
        </Button>
      </div>

      {/* Conversations List */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        <div className="p-2">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-sidebar-foreground/70" />
            </div>
          ) : chats && chats.length > 0 ? (
            chats.map((conversation) => (
              <div
                key={conversation.id}
                className={`w-full p-3 rounded-lg text-left hover:bg-sidebar-accent transition-colors mb-1 group relative ${
                  selectedConversationId === conversation.id 
                    ? 'bg-sidebar-accent border border-sidebar-border' 
                    : ''
                }`}
              >
                <button
                  onClick={() => handleSelectConversation(conversation.id)}
                  className="w-full text-left"
                >
                  <div className="flex items-start gap-3">
                    <MessageSquare className="h-4 w-4 text-sidebar-foreground/70 mt-1 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sidebar-foreground truncate mb-1">
                        {conversation.title}
                      </h3>
                      <p className="text-sidebar-foreground/70 text-sm truncate">
                        {conversation.last_message || 'No messages yet'}
                      </p>
                      <div className="flex items-center justify-between mt-1">
                        <p className="text-sidebar-foreground/50 text-xs">
                          {formatDistanceToNow(new Date(conversation.updated_at), { addSuffix: true })}
                        </p>
                        <button
                          onClick={(e) => handleDeleteClick(e, conversation.id)}
                          disabled={deletingChatId === conversation.id}
                          className="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-red-500/20 text-red-500 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                          title="Delete conversation"
                        >
                          {deletingChatId === conversation.id ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <Trash2 className="h-3 w-3" />
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                </button>
              </div>
            ))
          ) : (
            <div className="text-center py-8 text-sidebar-foreground/70">
              <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No conversations yet</p>
              <p className="text-xs mt-1">Start a new conversation to get started</p>
            </div>
          )}
          </div>
        </div>

      {/* Footer */}
      <div className="p-4 border-t border-sidebar-border flex-shrink-0">
        <div className="flex items-center justify-between gap-2">
          <Button
            variant="ghost"
            className="flex-1 justify-start text-sidebar-foreground hover:bg-sidebar-accent"
          >
            <Settings className="h-4 w-4 mr-2" />
            Settings
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="text-sidebar-foreground hover:bg-sidebar-accent"
            onClick={toggleTheme}
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? (
              <Sun className="h-4 w-4" />
            ) : (
              <Moon className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}