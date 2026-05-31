import { useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { HoverActions } from './HoverActions';
import { BrandMark } from './BrandMark';
import {
  CONTENT_TYPE_TEXT,
  CONTENT_TYPE_IMAGE,
  CONTENT_TYPE_WEBSITE,
  TOOL_CONVERSATION,
  TOOL_IMAGE_GENERATION,
  TOOL_WEBSITE_GENERATION,
} from '../constants/toolTypes';

function ImageBlock({ src, alt }) {
  const [status, setStatus] = useState('loading');
  return (
    <div className="mt-2 rounded-md overflow-hidden bg-muted/30 w-full max-w-sm border border-border/50">
      {status === 'loading' && (
        <div className="h-40 flex items-center justify-center text-xs font-brand-italic text-muted-foreground animate-pulse">
          Loading…
        </div>
      )}
      {status === 'error' && (
        <div className="h-40 flex items-center justify-center text-xs font-brand-italic text-muted-foreground">
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

const TOOL_LABELS = {
  image_generation: 'image · atelier',
  text_generation: 'copy · studio',
  video_generation: 'reel · motion',
  website_generation: 'site · house',
};

export function ChatMessage({ role, content, timestamp, image, html, tool }) {
  const isUser = role === 'user';
  const isVideo = tool === 'video_generation' || tool === 'video';
  // Decide rendering by actual file format: mp4/webm play in <video>;
  // animated webp (older ComfyUI output) and everything else go in <img>.
  const looksLikeVideoFile = image && (
    image.startsWith('data:video/') ||
    /\.(mp4|webm|mov)(\?|$)/i.test(image)
  );
  const showTextCopy =
    !isVideo && tool !== TOOL_IMAGE_GENERATION && tool !== TOOL_WEBSITE_GENERATION;
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
            className="rounded-2xl rounded-tr-md px-4 py-3 text-[15px] leading-relaxed border"
            style={{
              background: 'var(--user-bubble)',
              color: 'var(--user-bubble-fg)',
              borderColor: 'color-mix(in srgb, var(--accent) 30%, transparent)',
            }}
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
              className="rounded-md max-w-full max-h-48 object-contain ml-auto border border-border/50"
            />
          )}
        </div>
      </div>
    );
  }

  /* ── ASSISTANT MESSAGE ────────────────────────────────────────── */
  return (
    <div className="group flex gap-3 px-4 py-3">
      {/* Signature mark — Brandmate's hand on every reply */}
      <div
        className="flex-shrink-0 mt-1 h-7 w-7 rounded-md flex items-center justify-center"
        style={{
          background: 'color-mix(in srgb, var(--accent) 14%, transparent)',
          border: '1px solid color-mix(in srgb, var(--accent) 35%, var(--border))',
        }}
      >
        <BrandMark size={16} tone="duo" strokeWidth={1.6} />
      </div>

      <div className="min-w-0 flex-1 space-y-2">
        <HoverActions type={CONTENT_TYPE_TEXT} copyContent={showTextCopy ? content : null} enabled>
          <div className="prose prose-sm max-w-none dark:prose-invert text-foreground break-words leading-relaxed prose-headings:font-brand prose-headings:font-semibold">
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
            downloadFilename={
              looksLikeVideoFile ? 'video.mp4' : isVideo ? 'video.webp' : 'image.png'
            }
            className="w-fit"
            enabled
          >
            {looksLikeVideoFile ? (
              <video
                src={image}
                controls
                playsInline
                className="rounded-md max-w-sm max-h-72 object-contain border border-border/60 bg-black"
              />
            ) : (
              <img
                src={image}
                alt={isVideo ? 'Generated video' : 'Generated image'}
                className="rounded-md max-w-sm max-h-72 object-contain border border-border/60"
              />
            )}
          </HoverActions>
        )}

        {html && (
          <HoverActions
            type={CONTENT_TYPE_WEBSITE}
            downloadHtml={html}
            downloadFilename="landing-page.html"
            className="rounded-md border border-border overflow-hidden bg-white"
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
          <span
            className="inline-flex items-center gap-1.5 rounded-sm px-2 py-0.5 text-[10px] font-brand-italic tracking-wider"
            style={{
              background: 'color-mix(in srgb, var(--accent) 16%, transparent)',
              color: 'var(--muted-foreground)',
              border: '1px solid color-mix(in srgb, var(--accent) 30%, var(--border))',
            }}
          >
            <span
              className="inline-block h-1 w-1 rounded-full"
              style={{ background: 'var(--mark-soft)' }}
            />
            {TOOL_LABELS[tool] || tool}
          </span>
        )}
      </div>
    </div>
  );
}
