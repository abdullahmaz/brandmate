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
  Search,
  Bookmark,
  BookOpen,
  Sparkles,
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
  const [searchTerm, setSearchTerm] = useState('');
  const onToggle = () => setIsCollapsed((prev) => !prev);

  
  const selectedConversationId = location.pathname.split('/').pop();
  const query = searchTerm.trim().toLowerCase();
  const filteredChats = (chats || []).filter((conversation) => {
    const title = (conversation.title || '').toLowerCase();
    return query === '' || title.includes(query);
  });
  
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
      <div className="w-16 bg-sidebar border border-sidebar-border flex flex-col items-center py-4 gap-4 rounded-2xl shadow-xl shadow-black/5">
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
    <div className="w-[320px] flex-shrink-0 bg-sidebar/80 border border-sidebar-border rounded-2xl flex flex-col h-full shadow-2xl shadow-black/5 backdrop-blur-lg overflow-hidden">
      {/* Header */}
      <div className="px-4 py-4 border-b border-sidebar-border flex items-center justify-between">
        <div className="flex items-center gap-3">
            <p className="text-md font-semibold text-sidebar-foreground">Brandmate</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            className="text-sidebar-foreground hover:bg-sidebar-accent"
            onClick={toggleTheme}
            aria-label="Toggle theme"
          >
            {theme === 'light' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
          <Button variant="ghost" size="icon" onClick={onToggle} className="hover:bg-sidebar-accent">
            <PanelLeftClose className="h-5 w-5" />
          </Button>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto px-4 py-4 space-y-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-sidebar-foreground/50 dark:text-black" />
          <input
            type="text"
            placeholder="Search for chats..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full rounded-xl border border-sidebar-border bg-sidebar-accent/60 dark:bg-sidebar-accent/70 px-10 py-2 text-sm text-sidebar-foreground placeholder:text-sidebar-foreground/50 focus:outline-none focus:ring-2 focus:ring-sidebar-ring"
          />
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold text-sidebar-foreground">
              <BookOpen className="h-4 w-4 text-sidebar-foreground/60" />
              <span>Chat history</span>
            </div>
            <span className="rounded-full bg-sidebar-accent px-2 py-1 text-xs text-sidebar-foreground/70">
          {searchTerm.trim() ? filteredChats.length : chats?.length || 0} chat(s)
            </span>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-sidebar-foreground/70" />
            </div>
      ) : chats && chats.length > 0 ? (
        filteredChats.length > 0 ? (
          <div className="space-y-2">
            {filteredChats.map((conversation) => {
              const isSelected = selectedConversationId === conversation.id;
              return (
                <div
                  key={conversation.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => handleSelectConversation(conversation.id)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      handleSelectConversation(conversation.id);
                    }
                  }}
                  className={`group w-full rounded-xl border px-3 py-3 text-left shadow-sm transition hover:border-sidebar-ring hover:shadow-md focus:outline-none focus:ring-2 focus:ring-sidebar-ring ${
                    isSelected
                      ? 'border-sidebar-ring bg-sidebar-accent/80'
                      : 'border-sidebar-border bg-sidebar-accent/60 dark:bg-sidebar-accent/75'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className="h-8 w-8 rounded-full bg-sidebar-primary/15 text-sidebar-primary flex items-center justify-center">
                      <MessageSquare className="h-4 w-4" />
                    </div>
                    <div className="flex-1 min-w-0 space-y-1">
                      <div className="flex items-center justify-between gap-2">
                        <h3 className="line-clamp-2 text-sm font-semibold text-sidebar-foreground">
                          {conversation.title}
                        </h3>
                        <span className="text-[11px] text-sidebar-foreground/60">
                          {formatDistanceToNow(new Date(conversation.updated_at), { addSuffix: true })}
                        </span>
                      </div>
                      <div className="flex items-center justify-end pt-1">
                        <button
                          onClick={(e) => handleDeleteClick(e, conversation.id)}
                          disabled={deletingChatId === conversation.id}
                          className="rounded p-1 text-red-500 opacity-0 transition hover:bg-red-500/10 group-hover:opacity-100 disabled:opacity-50 disabled:cursor-not-allowed"
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
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-8 text-sidebar-foreground/70">
            <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm font-semibold">No conversations match your search</p>
            <p className="text-xs mt-1">Try a different title</p>
          </div>
        )
      ) : (
        <div className="text-center py-8 text-sidebar-foreground/70">
          <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm font-semibold">No conversations yet</p>
          <p className="text-xs mt-1">Start a new conversation to get started</p>
        </div>
      )}
        </div>
      </div>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-sidebar-border bg-sidebar/80">
        <div className="flex items-center justify-between gap-2 mb-3">
          <Button
            variant="ghost"
            className="flex-1 justify-start text-sidebar-foreground hover:bg-sidebar-accent"
          >
            <Settings className="h-4 w-4 mr-2" />
            Settings
          </Button>
        </div>
        <Button
          onClick={handleNewConversation}
          className="w-full rounded-xl bg-sidebar-primary text-sidebar-primary-foreground hover:bg-sidebar-primary/90 shadow-md shadow-sidebar-primary/20"
        >
          <PlusIcon className="h-4 w-4 mr-2" />
          Start new chat
        </Button>
      </div>
    </div>
  );
}