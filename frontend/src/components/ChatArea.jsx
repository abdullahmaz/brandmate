import { useEffect, useRef, useState } from 'react';
import { ScrollArea } from './ui/scroll-area';
import { ChatMessage } from './ChatMessage';
import {
  CHAT_LOADING_WORDS,
  CHAT_LOADING_WORD_ROTATE_MS,
} from '../constants/loadingWords';

/** Compact three-dot pulse (Claude Code–style), muted — no transform so scroll areas don’t clip */
function LoadingDots() {
  return (
    <div className="flex shrink-0 items-center gap-[3px] self-center" aria-hidden>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-[3px] w-[3px] shrink-0 rounded-full bg-muted-foreground motion-safe:animate-claude-loader-dot motion-reduce:animate-none motion-reduce:opacity-50"
          style={{ animationDelay: `${i * 0.14}s` }}
        />
      ))}
    </div>
  );
}

export function ChatArea({ messages, isLoading }) {
  const bottomRef = useRef(null);
  const [loadingWordIndex, setLoadingWordIndex] = useState(0);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  useEffect(() => {
    if (!isLoading) return;
    const pick = () =>
      Math.floor(Math.random() * CHAT_LOADING_WORDS.length);
    setLoadingWordIndex(pick());
    const id = setInterval(() => setLoadingWordIndex(pick()), CHAT_LOADING_WORD_ROTATE_MS);
    return () => clearInterval(id);
  }, [isLoading]);

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
          <div className="flex items-center gap-2 px-4 py-2">
            <LoadingDots />
            <p
              key={loadingWordIndex}
              className="min-w-0 flex-1 text-sm leading-relaxed text-muted-foreground motion-safe:animate-loading-line-in"
              role="status"
              aria-live="polite"
            >
              {CHAT_LOADING_WORDS[loadingWordIndex]}
            </p>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
