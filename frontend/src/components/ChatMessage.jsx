import { Avatar, AvatarFallback } from './ui/avatar';
import ReactMarkdown from 'react-markdown';

/**
 * Component for rendering a single chat message
 */
export function ChatMessage({ role, content, timestamp, image, html, tool }) {
  const isUser = role === 'user';
  const label = isUser ? 'You' : 'Assistant';

  const handleDownloadHtml = () => {
    if (!html) return;
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = 'landing-page.html';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const handleOpenPreviewInTab = () => {
    if (!html) return;
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank', 'noopener,noreferrer');
  };

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
          <div className="prose prose-sm max-w-none break-words leading-6 text-foreground dark:prose-invert">
            <ReactMarkdown>{content}</ReactMarkdown>
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

          {html && (
            <div className="mt-3 space-y-2">
              <div className="group relative rounded-xl border border-border/80 overflow-hidden bg-white max-h-[320px] min-h-[200px] flex flex-col">
                <button
                  type="button"
                  onClick={handleDownloadHtml}
                  className="absolute right-2 top-2 z-10 rounded-md bg-black/70 px-2 py-1 text-[11px] font-medium text-white opacity-0 shadow-sm transition-opacity group-hover:opacity-100 focus:opacity-100"
                >
                  Download HTML
                </button>
                <iframe
                  title="Landing page preview"
                  srcDoc={html}
                  sandbox="allow-same-origin"
                  className="w-full flex-1 min-h-[200px] border-0"
                  style={{ height: '320px' }}
                />
              </div>
              <button
                type="button"
                onClick={handleOpenPreviewInTab}
                className="text-xs text-primary hover:underline"
              >
                Open in new tab
              </button>
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
