import { useEffect, useRef, useState } from 'react';
import { ScrollArea } from './ui/scroll-area';
import { ChatMessage } from './ChatMessage';
import { BrandMark } from './BrandMark';
import {
  CHAT_LOADING_WORDS,
  CHAT_LOADING_WORD_ROTATE_MS,
} from '../constants/loadingWords';

/** Dual conic rings + core pulse — see `@layer components` in globals.css */
function ChatLoadingSpinner() {
  return (
    <div className="chat-loading-spinner" aria-hidden>
      <div className="chat-loading-spinner__ring chat-loading-spinner__ring--outer" />
      <div className="chat-loading-spinner__ring chat-loading-spinner__ring--inner" />
      <div className="chat-loading-spinner__core" />
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
          <div className="flex gap-3 px-4 py-3">
            <div
              className="flex-shrink-0 mt-1 h-7 w-7 rounded-md flex items-center justify-center"
              style={{
                background: 'color-mix(in srgb, var(--accent) 14%, transparent)',
                border: '1px solid color-mix(in srgb, var(--accent) 35%, var(--border))',
              }}
            >
              <BrandMark size={16} tone="duo" strokeWidth={1.6} />
            </div>
            <div className="flex items-center gap-2 min-w-0 flex-1 pt-1">
              <ChatLoadingSpinner />
              <p
                key={loadingWordIndex}
                className="min-w-0 flex-1 font-brand-italic text-[15px] leading-relaxed text-muted-foreground motion-safe:animate-loading-line-in"
                role="status"
                aria-live="polite"
              >
                {CHAT_LOADING_WORDS[loadingWordIndex]}…
              </p>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
