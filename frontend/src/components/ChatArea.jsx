import { useEffect, useRef } from 'react';
import { ScrollArea } from './ui/scroll-area';
import { ChatMessage } from './ChatMessage';

/**
 * @typedef {Object} Message
 * @property {string} id
 * @property {'user' | 'assistant'} role
 * @property {string} content
 * @property {string} timestamp
 */

/**
 * @typedef {Object} ChatAreaProps
 * @property {Message[]} messages
 * @property {boolean} [isLoading]
 */

/**
 * Component for displaying chat messages
 * @param {ChatAreaProps} props
 */
export function ChatArea({ messages, isLoading }) {
  const scrollAreaRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center h-full">
        <div className="text-center space-y-4 max-w-md">
          <div className="w-16 h-16 mx-auto bg-primary/10 rounded-full flex items-center justify-center">
            <span className="text-2xl">🌿</span>
          </div>
          <h3 className="text-foreground font-medium">Welcome to your AI Assistant</h3>
          <p className="text-muted-foreground">
            Start a conversation by typing a message below. I'm here to help with any questions you might have.
          </p>
        </div>
      </div>
    );
  }

  return (
    <ScrollArea className="flex-1" ref={scrollAreaRef}>
      <div className="max-w-4xl mx-auto">
        {messages.map((message) => (
          <ChatMessage
            key={message.id}
            role={message.role}
            content={message.content}
            timestamp={message.timestamp}
            image={message.image}
            tool={message.tool}
          />
        ))}
        
        {isLoading && (
          <div className="flex gap-4 p-6">
            <div className="w-8 h-8 bg-accent rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-accent-foreground text-sm">AI</span>
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-foreground">Assistant</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce"></div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
    </ScrollArea>
  );
}
