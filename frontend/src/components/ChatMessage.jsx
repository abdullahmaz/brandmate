import { useMemo } from 'react';
import { Avatar, AvatarFallback } from './ui/avatar';
import ReactMarkdown from 'react-markdown';
import { HoverActions } from './HoverActions';
import { CONTENT_TYPE_TEXT, CONTENT_TYPE_IMAGE, CONTENT_TYPE_WEBSITE, TOOL_CONVERSATION } from '../constants/toolTypes';

/**
 * Component for rendering a single chat message
 */
export function ChatMessage({ role, content, timestamp, image, html, tool }) {
  const isUser = role === 'user';
  const label = isUser ? 'You' : 'Assistant';
  const iframeSrcDoc = useMemo(() =>
    html ? html + `<script>document.addEventListener('click',function(e){var a=e.target.closest('a[href^="#"]');if(a){e.preventDefault();var el=document.querySelector(a.getAttribute('href'));if(el)el.scrollIntoView({behavior:'smooth'});}});<\/script>` : null,
    [html]
  );

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
          <HoverActions type={CONTENT_TYPE_TEXT} copyContent={content} enabled={!isUser}>
            <div className="prose prose-sm max-w-none break-words leading-6 text-foreground dark:prose-invert">
              <ReactMarkdown>{content}</ReactMarkdown>
            </div>
          </HoverActions>

          {image && (
            <div className="mt-3">
              <HoverActions type={CONTENT_TYPE_IMAGE} downloadUrl={image} downloadFilename="image.png" className="w-fit" enabled={!isUser}>
                <img
                  src={image}
                  alt="Generated content"
                  className="rounded-xl max-w-full max-h-[320px] object-contain"
                />
              </HoverActions>
            </div>
          )}

          {html && (
            <div className="mt-3 space-y-2">
              <HoverActions type={CONTENT_TYPE_WEBSITE} downloadHtml={html} downloadFilename="landing-page.html" className="rounded-xl border border-border/80 overflow-hidden bg-white max-h-[320px] min-h-[200px] flex flex-col" enabled={!isUser}>
                <iframe
                  title="Landing page preview"
                  srcDoc={iframeSrcDoc}
                  sandbox="allow-same-origin allow-scripts"
                  className="w-full flex-1 min-h-[400px] border-0"
                />
              </HoverActions>
            </div>
          )}

          {tool && tool !== TOOL_CONVERSATION && (
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
