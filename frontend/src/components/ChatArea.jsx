import { useEffect, useRef } from 'react';
import { ScrollArea } from './ui/scroll-area';
import { ChatMessage } from './ChatMessage';
import { Spinner } from './ui/spinner';

/**
 * Component for displaying chat messages
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
      <div className="flex-1 flex items-center justify-center h-full px-6">
        <Spinner variant="ellipsis" size={24} className="text-primary" />
      </div>
    );
  }

  return (
    <ScrollArea className="flex-1 h-full" ref={scrollAreaRef}>
      <div className="mx-auto max-w-3xl py-6">
        <div className="flex justify-center pb-2">
          <span className="rounded-full bg-muted/70 px-3 py-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Today
          </span>
        </div>

        {messages.map((message) => (
          <ChatMessage
            key={message.id}
            role={message.role}
            content={message.content}
            timestamp={message.timestamp}
            image={message.image}
            html={message.html}
            tool={message.tool}
          />
        ))}
        
        {isLoading && (
          <div className="flex gap-4 px-4 py-5">
            <div className="h-10 w-10 rounded-full bg-accent text-accent-foreground flex items-center justify-center flex-shrink-0">
              <span className="text-sm font-semibold">AI</span>
            </div>
            <div className="flex-1">
              <div className="rounded-2xl border border-border/70 bg-card/90 px-4 py-3 shadow-sm">
                <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
                  Assistant
                  <span className="text-xs text-muted-foreground">is thinking</span>
                  <Spinner variant="ellipsis" size={16} className="text-primary" />
                </div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
    </ScrollArea>
  );
}
