import { useState, useRef, useEffect } from 'react';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Send, StopCircle, Image, X } from 'lucide-react';

/**
 * Component for chat input with send button and image upload
 */
export function ChatInput({
  onSendMessage,
  isLoading = false,
  onStop,
  placeholder = 'How can I help you today?',
}) {
  const [message, setMessage] = useState('');
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    const hasContent = message.trim() || imageFile;
    if (hasContent && !isLoading) {
      onSendMessage(message.trim(), imageFile);
      setMessage('');
      setImageFile(null);
      setImagePreview(null);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleStop = () => {
    if (onStop) onStop();
  };

  const handleImageClick = () => {
    fileInputRef.current?.click();
  };

  const handleImageChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Only allow image files
    if (!file.type.startsWith('image/')) {
      alert('Please select an image file.');
      return;
    }

    setImageFile(file);

    // Generate preview URL
    const reader = new FileReader();
    reader.onloadend = () => {
      setImagePreview(reader.result);
    };
    reader.readAsDataURL(file);

    // Reset file input so the same file can be re-selected
    e.target.value = '';
  };

  const handleRemoveImage = () => {
    setImageFile(null);
    setImagePreview(null);
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'inherit';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [message]);

  const canSend = (message.trim() || imageFile) && !isLoading;

  return (
    <div className="bg-transparent pb-6">
      <div className="max-w-3xl mx-auto px-4">
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={handleImageChange}
        />

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="relative rounded-2xl border border-border/80 bg-card/90 shadow-xl shadow-black/5">
            <div className="p-4 space-y-3">

              {/* Image preview */}
              {imagePreview && (
                <div className="relative inline-block">
                  <img
                    src={imagePreview}
                    alt="Selected"
                    className="h-24 w-24 rounded-lg object-cover border border-border/60"
                  />
                  <button
                    type="button"
                    onClick={handleRemoveImage}
                    className="absolute -top-2 -right-2 flex h-5 w-5 items-center justify-center rounded-full bg-foreground text-background shadow-md hover:bg-foreground/80 transition-colors"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              )}

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

                <div className="flex items-center gap-2">
                  {/* Image upload button */}
                  <Button
                    type="button"
                    onClick={handleImageClick}
                    size="sm"
                    variant="ghost"
                    disabled={isLoading}
                    className="flex items-center gap-1.5 rounded-full text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
                    title="Attach image"
                  >
                    <Image className="h-4 w-4" />
                    {imageFile ? (
                      <span className="text-xs text-primary font-medium">1 image</span>
                    ) : (
                      <span className="text-xs">Image</span>
                    )}
                  </Button>

                  {/* Send / Stop button */}
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
                      disabled={!canSend}
                      className="rounded-full px-4 bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
                    >
                      <Send className="h-4 w-4 mr-2" />
                      Send message
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}