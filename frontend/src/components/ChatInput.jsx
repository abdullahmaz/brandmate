import { useState, useRef, useEffect } from 'react';
import { Button } from './ui/button';
import { ArrowUp, Square, Paperclip, X } from 'lucide-react';

export function ChatInput({
  onSendMessage,
  isLoading = false,
  onStop,
  placeholder = 'Message Brandmate',
}) {
  const [message, setMessage] = useState('');
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  const canSend = !!(message.trim() || imageFile) && !isLoading;

  const submit = (e) => {
    e?.preventDefault();
    if (!canSend && !isLoading) return;
    if (isLoading) { onStop?.(); return; }
    onSendMessage(message.trim(), imageFile);
    setMessage('');
    setImageFile(null);
    setImagePreview(null);
  };

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); }
  };

  const pickImage = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImageFile(file);
    const reader = new FileReader();
    reader.onloadend = () => setImagePreview(reader.result);
    reader.readAsDataURL(file);
    e.target.value = '';
  };

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = `${Math.min(ta.scrollHeight, 200)}px`;
  }, [message]);

  return (
    <div className="px-4 pb-5 pt-2">
      <div className="mx-auto max-w-2xl">
        <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={pickImage} />

        <div className="rounded-2xl border border-border bg-input shadow-sm transition-shadow focus-within:shadow-md focus-within:border-ring/60">
          {/* Image preview strip */}
          {imagePreview && (
            <div className="px-3 pt-3">
              <div className="relative inline-block">
                <img src={imagePreview} alt="Preview" className="h-20 w-20 rounded-lg object-cover border border-border/40" />
                <button
                  type="button"
                  onClick={() => { setImageFile(null); setImagePreview(null); }}
                  className="absolute -top-1.5 -right-1.5 h-5 w-5 rounded-full bg-foreground text-background flex items-center justify-center hover:opacity-80 transition-opacity"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            </div>
          )}

          {/* Textarea */}
          <div className="px-4 pt-3 pb-1">
            <textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={onKey}
              placeholder={placeholder}
              disabled={isLoading}
              rows={1}
              className="w-full resize-none bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none leading-6 max-h-[200px]"
            />
          </div>

          {/* Toolbar */}
          <div className="flex items-center justify-between px-3 pb-2.5 pt-1">
            <Button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              size="icon"
              variant="ghost"
              disabled={isLoading}
              className="h-8 w-8 rounded-full text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
              title="Attach image"
            >
              <Paperclip className="h-4 w-4" />
            </Button>

            {isLoading ? (
              <button
                type="button"
                onClick={onStop}
                className="h-8 w-8 rounded-full bg-foreground text-background flex items-center justify-center hover:opacity-80 transition-opacity"
                title="Stop"
              >
                <Square className="h-3.5 w-3.5" />
              </button>
            ) : (
              <button
                type="button"
                onClick={submit}
                disabled={!canSend}
                className="h-8 w-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 disabled:opacity-35 disabled:cursor-not-allowed transition-all"
                title="Send"
              >
                <ArrowUp className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
