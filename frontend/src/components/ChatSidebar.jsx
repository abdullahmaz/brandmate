import { useState } from 'react';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { Separator } from './ui/separator';
import { PlusIcon, MessageSquare, PanelLeftClose, Settings } from 'lucide-react';

/**
 * @typedef {Object} Conversation
 * @property {string} id
 * @property {string} title
 * @property {string} lastMessage
 * @property {string} timestamp
 */

/**
 * @typedef {Object} ChatSidebarProps
 * @property {boolean} isCollapsed
 * @property {() => void} onToggle
 * @property {string|null} selectedConversationId
 * @property {(id: string) => void} onSelectConversation
 * @property {() => void} onNewConversation
 */

/**
 * Chat sidebar component that shows conversations list
 * @param {ChatSidebarProps} props 
 */
export function ChatSidebar({ 
  isCollapsed, 
  onToggle, 
  selectedConversationId, 
  onSelectConversation, 
  onNewConversation 
}) {
  const [conversations] = useState([
    {
      id: '1',
      title: 'Light Sea Green Design',
      lastMessage: 'I want a simple LLM interface like claude...',
      timestamp: 'Just now'
    },
    {
      id: '2',
      title: 'React Components Help',
      lastMessage: 'How to create reusable components?',
      timestamp: '2 hours ago'
    },
    {
      id: '3',
      title: 'Tailwind CSS Tips',
      lastMessage: 'Best practices for styling...',
      timestamp: 'Yesterday'
    },
    {
      id: '4',
      title: 'TypeScript Questions',
      lastMessage: 'Interface vs type definitions',
      timestamp: '2 days ago'
    }
  ]);

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
          onClick={onNewConversation}
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
    <div className="w-80 bg-sidebar border-r border-sidebar-border flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-sidebar-border">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sidebar-foreground font-bold">Brandmate</h3>
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggle}
            className="text-sidebar-foreground hover:bg-sidebar-accent"
          >
            <PanelLeftClose className="h-5 w-5" />
          </Button>
        </div>
        <Button 
          onClick={onNewConversation}
          className="w-full bg-sidebar-primary text-sidebar-primary-foreground hover:bg-sidebar-primary/90"
        >
          <PlusIcon className="h-4 w-4 mr-2" />
          New Conversation
        </Button>
      </div>

      {/* Conversations List */}
      <ScrollArea className="flex-1">
        <div className="p-2">
          {conversations.map((conversation) => (
            <button
              key={conversation.id}
              onClick={() => onSelectConversation(conversation.id)}
              className={`w-full p-3 rounded-lg text-left hover:bg-sidebar-accent transition-colors mb-1 ${
                selectedConversationId === conversation.id 
                  ? 'bg-sidebar-accent border border-sidebar-border' 
                  : ''
              }`}
            >
              <div className="flex items-start gap-3">
                <MessageSquare className="h-4 w-4 text-sidebar-foreground/70 mt-1 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <h3 className="text-sidebar-foreground truncate mb-1">
                    {conversation.title}
                  </h3>
                  <p className="text-sidebar-foreground/70 text-sm truncate">
                    {conversation.lastMessage}
                  </p>
                  <p className="text-sidebar-foreground/50 text-xs mt-1">
                    {conversation.timestamp}
                  </p>
                </div>
              </div>
            </button>
          ))}
        </div>
      </ScrollArea>

      {/* Footer */}
      <div className="p-4 border-t border-sidebar-border">
        <Button
          variant="ghost"
          className="w-full justify-start text-sidebar-foreground hover:bg-sidebar-accent"
        >
          <Settings className="h-4 w-4 mr-2" />
          Settings
        </Button>
      </div>
    </div>
  );
}
