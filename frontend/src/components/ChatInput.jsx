import { useState, useRef, useEffect, forwardRef, useImperativeHandle } from 'react';
import { Button } from './ui/button';
import { ArrowUp, Square, Paperclip, X, Settings2, Zap, Scale, Sparkles, Check } from 'lucide-react';

const QUALITY_OPTIONS = [
  { value: 'speed',    label: 'Speed',    desc: '6s · choppier playback (8 fps)', icon: Zap },
  { value: 'balanced', label: 'Balanced', desc: '6s · smooth (12 fps)',          icon: Scale },
  { value: 'quality',  label: 'Quality',  desc: '6s · native fps, smoothest (16 fps)', icon: Sparkles },
];

export const ChatInput = forwardRef(function ChatInput(
  {
    onSendMessage,
    isLoading = false,
    onStop,
    placeholder = 'Sketch a brief — for an Eid drop, a campaign, a launch…',
    qualityMode = 'balanced',
    onQualityModeChange,
  },
  ref,
) {
  const [message, setMessage] = useState('');
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const settingsRef = useRef(null);

  // Close popover on outside click.
  useEffect(() => {
    if (!settingsOpen) return;
    const onDocClick = (e) => {
      if (!settingsRef.current?.contains(e.target)) setSettingsOpen(false);
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [settingsOpen]);

  useImperativeHandle(ref, () => ({
    setMessage: (text) => {
      setMessage(text);
      // focus after state flush
      requestAnimationFrame(() => textareaRef.current?.focus());
    },
    focus: () => textareaRef.current?.focus(),
  }));

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

        <div className="editorial-input">
          {/* Image preview strip */}
          {imagePreview && (
            <div className="px-3 pt-3">
              <div className="relative inline-block">
                <img src={imagePreview} alt="Preview" className="h-20 w-20 rounded-md object-cover border border-border" />
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
          <div className="px-4 pt-3.5 pb-1">
            <textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={onKey}
              placeholder={placeholder}
              disabled={isLoading}
              rows={1}
              className="w-full resize-none bg-transparent text-[15px] text-foreground placeholder:text-muted-foreground placeholder:font-brand-italic outline-none leading-6 max-h-[200px]"
            />
          </div>

          {/* Toolbar */}
          <div className="flex items-center justify-between px-3 pb-2.5 pt-1">
            <div className="flex items-center gap-1">
              <Button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                size="icon"
                variant="ghost"
                disabled={isLoading}
                className="h-8 w-8 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
                title="Attach reference"
              >
                <Paperclip className="h-4 w-4" />
              </Button>

              {/* Video quality settings */}
              <div className="relative" ref={settingsRef}>
                <Button
                  type="button"
                  onClick={() => setSettingsOpen((v) => !v)}
                  size="icon"
                  variant="ghost"
                  disabled={isLoading}
                  className="h-8 w-8 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
                  title="Video quality"
                  aria-haspopup="menu"
                  aria-expanded={settingsOpen}
                >
                  <Settings2 className="h-4 w-4" />
                </Button>
                {settingsOpen && (
                  <div
                    role="menu"
                    className="absolute bottom-full left-0 mb-2 w-64 rounded-md border border-border bg-card shadow-lg overflow-hidden z-10"
                  >
                    <div className="px-3 py-2 border-b border-border">
                      <p className="font-brand text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                        Video quality
                      </p>
                      <p className="font-brand-italic text-[11px] text-muted-foreground/70 mt-0.5">
                        Trade speed for length & quality
                      </p>
                    </div>
                    {QUALITY_OPTIONS.map((opt) => {
                      const Icon = opt.icon;
                      const active = qualityMode === opt.value;
                      return (
                        <button
                          key={opt.value}
                          type="button"
                          role="menuitemradio"
                          aria-checked={active}
                          onClick={() => {
                            onQualityModeChange?.(opt.value);
                            setSettingsOpen(false);
                          }}
                          className={`w-full flex items-start gap-2.5 px-3 py-2 text-left hover:bg-muted/60 transition-colors ${
                            active ? 'bg-muted/50' : ''
                          }`}
                        >
                          <Icon className="h-3.5 w-3.5 mt-0.5 flex-shrink-0 text-foreground" />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="text-[13px] font-medium text-foreground">{opt.label}</span>
                              {active && <Check className="h-3 w-3 text-foreground" />}
                            </div>
                            <p className="text-[11px] text-muted-foreground leading-snug">{opt.desc}</p>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              <span className="font-brand-italic text-[11px] text-muted-foreground/70 select-none hidden sm:inline">
                attach a swatch, sketch or reference
              </span>
            </div>

            {isLoading ? (
              <button
                type="button"
                onClick={onStop}
                className="h-8 w-8 rounded-md bg-foreground text-background flex items-center justify-center hover:opacity-80 transition-opacity"
                title="Stop"
              >
                <Square className="h-3.5 w-3.5" />
              </button>
            ) : (
              <button
                type="button"
                onClick={submit}
                disabled={!canSend}
                className="send-btn h-8 w-8 rounded-md flex items-center justify-center"
                title="Send"
              >
                <ArrowUp className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>

        <p className="mt-2 text-center font-brand-italic text-[11px] text-muted-foreground/65 select-none">
          Brandmate stitches with AI. Review every cut before it ships.
        </p>
      </div>
    </div>
  );
});
