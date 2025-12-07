import { useState, useRef, useEffect } from 'react';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Send, StopCircle, Paperclip, BookOpen, Image, Mic, Smile } from 'lucide-react';

/**
 * Component for chat input with send button
 */
export function ChatInput({
  onSendMessage,
  isLoading = false,
  onStop,
  placeholder = 'How can I help you today?',
}) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !isLoading) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleStop = () => {
    if (onStop) {
      onStop();
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'inherit';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [message]);

  return (
    <div className="bg-transparent pb-6">
      <div className="max-w-3xl mx-auto px-4">
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="relative rounded-2xl border border-border/80 bg-card/90 shadow-xl shadow-black/5">
            <div className="p-4">
              <Textarea
                ref={textareaRef}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={placeholder}
                className="flex-1 min-h-[44px] max-h-32 resize-none border-0 bg-transparent p-0 text-base leading-6 focus:ring-0 focus-visible:ring-0"
                disabled={isLoading}
                rows={1}
              />

              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Press Enter to send, Shift+Enter for new line</span>

                {isLoading ? (
                  <Button
                    type="button"
                    onClick={handleStop}
                    size="sm"
                    variant="ghost"
                    className="flex items-center gap-2 rounded-full text-muted-foreground hover:text-foreground"
                  >
                    <StopCircle className="h-4 w-4" />
                    Stop
                  </Button>
                ) : (
                  <Button
                    type="submit"
                    size="sm"
                    disabled={!message.trim() || isLoading}
                    className="rounded-full px-4 bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
                  >
                    <Send className="h-4 w-4 mr-2" />
                    Send message
                  </Button>
                )}
              </div>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
