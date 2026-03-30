import { useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { HoverActions } from './HoverActions';
import {
  CONTENT_TYPE_TEXT,
  CONTENT_TYPE_IMAGE,
  CONTENT_TYPE_WEBSITE,
  TOOL_CONVERSATION,
} from '../constants/toolTypes';
import { Sparkles } from 'lucide-react';

function ImageBlock({ src, alt }) {
  const [status, setStatus] = useState('loading');
  return (
    <div className="mt-2 rounded-xl overflow-hidden border border-border/40 bg-muted/20 w-full max-w-sm">
      {status === 'loading' && (
        <div className="h-40 flex items-center justify-center text-xs text-muted-foreground animate-pulse">
          Loading…
        </div>
      )}
      {status === 'error' && (
        <div className="h-40 flex items-center justify-center text-xs text-muted-foreground">
          Image unavailable
        </div>
      )}
      <img
        src={src}
        alt={alt}
        className={`w-full max-h-[300px] object-cover ${status !== 'loaded' ? 'hidden' : ''}`}
        onLoad={() => setStatus('loaded')}
        onError={() => setStatus('error')}
      />
    </div>
  );
}

function splitContent(content) {
  if (!content) return [{ type: 'text', value: content }];
  const parts = [];
  const re = /!\[([^\]]*)\]\(([^)]+)\)/g;
  let last = 0, m;
  while ((m = re.exec(content)) !== null) {
    if (m.index > last) parts.push({ type: 'text', value: content.slice(last, m.index) });
    parts.push({ type: 'image', alt: m[1], src: m[2] });
    last = m.index + m[0].length;
  }
  if (last < content.length) parts.push({ type: 'text', value: content.slice(last) });
  return parts;
}

export function ChatMessage({ role, content, timestamp, image, html, tool }) {
  const isUser = role === 'user';
  const isVideo = tool === 'video_generation' || tool === 'video';
  const iframeSrcDoc = useMemo(() =>
    html
      ? html + `<script>document.addEventListener('click',function(e){var a=e.target.closest('a[href]');if(!a)return;var h=a.getAttribute('href');if(h&&h.startsWith('#')){e.preventDefault();var el=document.querySelector(h);if(el)el.scrollIntoView({behavior:'smooth'});}else{e.preventDefault();}});<\/script>`
      : null,
    [html]
  );
  const parts = useMemo(() => splitContent(content), [content]);

  /* ── USER MESSAGE ─────────────────────────────────────────────── */
  if (isUser) {
    return (
      <div className="flex justify-end px-4 py-2">
        <div className="max-w-[75%] space-y-2">
          <div
            className="rounded-3xl px-4 py-3 text-sm leading-relaxed"
            style={{ background: 'var(--user-bubble)', color: 'var(--user-bubble-fg)' }}
          >
            {parts.map((p, i) =>
              p.type === 'image' ? (
                <ImageBlock key={i} src={p.src} alt={p.alt} />
              ) : (
                <div key={i} className="prose prose-sm max-w-none dark:prose-invert break-words">
                  <ReactMarkdown>{p.value}</ReactMarkdown>
                </div>
              )
            )}
          </div>
          {image && (
            <img
              src={image}
              alt="Uploaded"
              className="rounded-xl max-w-full max-h-48 object-contain ml-auto"
            />
          )}
        </div>
      </div>
    );
  }

  /* ── ASSISTANT MESSAGE ────────────────────────────────────────── */
  return (
    <div className="group flex gap-3 px-4 py-2">
      {/* Avatar */}
      <div className="mt-1 flex-shrink-0 h-7 w-7 rounded-full bg-primary flex items-center justify-center">
        <Sparkles className="h-3.5 w-3.5 text-primary-foreground" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 space-y-2">
        <HoverActions type={CONTENT_TYPE_TEXT} copyContent={content} enabled>
          <div className="prose prose-sm max-w-none dark:prose-invert text-foreground break-words leading-relaxed">
            {parts.map((p, i) =>
              p.type === 'image' ? (
                <ImageBlock key={i} src={p.src} alt={p.alt} />
              ) : (
                <ReactMarkdown key={i}>{p.value}</ReactMarkdown>
              )
            )}
          </div>
        </HoverActions>

        {image && (
          <HoverActions
            type={CONTENT_TYPE_IMAGE}
            downloadUrl={image}
            downloadFilename={isVideo ? 'video.webp' : 'image.png'}
            className="w-fit"
            enabled
          >
            <img
              src={image}
              alt={isVideo ? 'Generated video' : 'Generated image'}
              className="rounded-xl max-w-sm max-h-72 object-contain border border-border/40"
            />
          </HoverActions>
        )}

        {html && (
          <HoverActions
            type={CONTENT_TYPE_WEBSITE}
            downloadHtml={html}
            downloadFilename="landing-page.html"
            className="rounded-xl border border-border/60 overflow-hidden bg-white"
            enabled
          >
            <iframe
              title="Preview"
              srcDoc={iframeSrcDoc}
              sandbox="allow-same-origin allow-scripts"
              className="w-full min-h-[400px] border-0"
            />
          </HoverActions>
        )}

        {tool && tool !== TOOL_CONVERSATION && (
          <span className="inline-flex items-center gap-1 rounded-md bg-muted/60 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            {tool}
          </span>
        )}
      </div>
    </div>
  );
}
