import { useState, useRef, useEffect } from 'react';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Send, StopCircle } from 'lucide-react';

/**
 * @typedef {Object} ChatInputProps
 * @property {(message: string) => void} onSendMessage
 * @property {boolean} [isLoading]
 * @property {() => void} [onStop]
 * @property {string} [placeholder]
 */

/**
 * Component for chat input with send button
 * @param {ChatInputProps} props
 */
export function ChatInput({ 
  onSendMessage, 
  isLoading = false, 
  onStop, 
  placeholder = "How can I help you today?" 
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
    <div className="bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="max-w-4xl mx-auto p-4">
        <form onSubmit={handleSubmit} className="relative">
          <div className="relative flex items-end gap-3 bg-card rounded-lg p-3 shadow-sm">
            <Textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              className="flex-1 min-h-[44px] max-h-32 resize-none border-0 bg-transparent p-0 focus:ring-0 focus-visible:ring-0"
              disabled={isLoading}
              rows={1}
            />
            
            {isLoading ? (
              <Button
                type="button"
                onClick={handleStop}
                size="icon"
                variant="ghost"
                className="flex-shrink-0 text-muted-foreground hover:text-foreground"
              >
                <StopCircle className="h-5 w-5" />
              </Button>
            ) : (
              <Button
                type="submit"
                size="icon"
                disabled={!message.trim() || isLoading}
                className="flex-shrink-0 bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                <Send className="h-4 w-4" />
              </Button>
            )}
          </div>
          
          <p className="text-xs text-muted-foreground text-center mt-2">
            Press Enter to send, Shift+Enter for new line
          </p>
        </form>
      </div>
    </div>
  );
}
