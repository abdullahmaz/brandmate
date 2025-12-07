import { Avatar, AvatarFallback } from './ui/avatar';

/**
 * Component for rendering a single chat message
 */
export function ChatMessage({ role, content, timestamp, image, tool }) {
  const isUser = role === 'user';
  const label = isUser ? 'You' : 'Assistant';

  return (
    <div className="flex gap-4 px-4 py-5">
      <Avatar className="h-10 w-10 flex-shrink-0">
        <AvatarFallback className={isUser ? 'bg-primary text-primary-foreground' : 'bg-accent text-accent-foreground'}>
          {isUser ? 'U' : 'AI'}
        </AvatarFallback>
      </Avatar>

      <div className="flex-1 min-w-0 space-y-2">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="font-semibold text-foreground">{label}</span>
          {timestamp && <span className="text-muted-foreground/80">{timestamp}</span>}
        </div>

        <div
          className={`rounded-2xl border border-border/80 bg-card/90 px-4 py-3 shadow-sm backdrop-blur-sm ${
            isUser ? 'shadow-primary/10' : 'shadow-black/5'
          }`}
        >
          <div className="whitespace-pre-wrap break-words text-sm leading-6 text-foreground">
            {content}
          </div>

          {image && (
            <div className="mt-3">
              <img
                src={image}
                alt="Generated content"
                className="rounded-xl max-w-full max-h-[320px] object-contain"
              />
            </div>
          )}

          {tool && tool !== 'conversation' && (
            <div className="mt-3 inline-flex items-center gap-2 rounded-full bg-accent px-3 py-1 text-[11px] text-accent-foreground/80">
              <span className="font-medium text-foreground">Tool</span>
              <span className="uppercase tracking-wide text-muted-foreground">{tool}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
