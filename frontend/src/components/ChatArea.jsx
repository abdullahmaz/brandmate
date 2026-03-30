import { useEffect, useRef } from 'react';
import { ScrollArea } from './ui/scroll-area';
import { ChatMessage } from './ChatMessage';
import { Spinner } from './ui/spinner';
import { Sparkles } from 'lucide-react';

export function ChatArea({ messages, isLoading }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <ScrollArea className="h-full">
      <div className="mx-auto max-w-2xl pb-6 pt-8">
        {messages.map((msg) => (
          <ChatMessage
            key={msg.id}
            role={msg.role}
            content={msg.content}
            timestamp={msg.timestamp}
            image={msg.image}
            html={msg.html}
            tool={msg.tool}
          />
        ))}

        {isLoading && (
          <div className="flex gap-3 px-4 py-2">
            <div className="mt-1 flex-shrink-0 h-7 w-7 rounded-full bg-primary flex items-center justify-center">
              <Sparkles className="h-3.5 w-3.5 text-primary-foreground" />
            </div>
            <div className="flex items-center pt-1.5">
              <Spinner variant="ellipsis" size={20} className="text-muted-foreground" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
