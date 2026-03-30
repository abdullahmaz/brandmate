import { useEffect, useRef, useState } from 'react';
import { Check, Copy, Download, ExternalLink } from 'lucide-react';
import { CONTENT_TYPE_TEXT, CONTENT_TYPE_IMAGE, CONTENT_TYPE_WEBSITE } from '../constants/toolTypes';
import { toast } from '@/hooks/use-toast';

const API_BASE = 'http://localhost:8000';

/**
 * Wrapper that shows hover actions: copy for text, download for image/website.
 */
export function HoverActions({
  children,
  type,
  copyContent,
  downloadUrl,
  downloadFilename,
  downloadHtml,
  className = '',
  enabled = true,
}) {
  const [copied, setCopied] = useState(false);
  const copiedTimerRef = useRef(null);

  useEffect(() => {
    return () => {
      if (copiedTimerRef.current) {
        clearTimeout(copiedTimerRef.current);
        copiedTimerRef.current = null;
      }
    };
  }, []);

  const markCopied = () => {
    setCopied(true);
    if (copiedTimerRef.current) clearTimeout(copiedTimerRef.current);
    copiedTimerRef.current = setTimeout(() => {
      setCopied(false);
      copiedTimerRef.current = null;
    }, 1200);

    toast({
      variant: 'info',
      title: 'Copied',
      description: 'Text copied to clipboard.',
    });
  };

  const handleCopy = async () => {
    if (type !== CONTENT_TYPE_TEXT || copyContent == null) return;
    await navigator.clipboard.writeText(copyContent);
    markCopied();
  };

  const handleDownload = async () => {
    if (type === CONTENT_TYPE_IMAGE && downloadUrl) {
      try {
        const isVideoFile = downloadFilename && downloadFilename.endsWith('.webp');
        // Videos → convert to MP4; images → proxy for CORS bypass
        const proxyUrl = downloadUrl.startsWith('data:')
          ? downloadUrl  // base64 data URL — use directly
          : isVideoFile
            ? `${API_BASE}/api/convert-video?url=${encodeURIComponent(downloadUrl)}`
            : `${API_BASE}/api/image-proxy?url=${encodeURIComponent(downloadUrl)}`;
        const filename = isVideoFile ? 'video.mp4' : (downloadFilename || 'image.png');

        const res = await fetch(proxyUrl);
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      } catch {
        window.open(downloadUrl, '_blank', 'noopener,noreferrer');
      }
    } else if (type === CONTENT_TYPE_WEBSITE && downloadHtml) {
      const blob = new Blob([downloadHtml], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = downloadFilename || 'landing-page.html';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    }
  };

  const handleOpenInNewTab = () => {
    if (type === CONTENT_TYPE_WEBSITE && downloadHtml) {
      const blob = new Blob([downloadHtml], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank', 'noopener,noreferrer');
    }
  };

  const showCopy = enabled && type === CONTENT_TYPE_TEXT && copyContent != null;
  const showDownload = enabled && ((type === CONTENT_TYPE_IMAGE && downloadUrl) || (type === CONTENT_TYPE_WEBSITE && downloadHtml));
  const showOpenInNewTab = enabled && type === CONTENT_TYPE_WEBSITE && downloadHtml;

  if (!showCopy && !showDownload && !showOpenInNewTab) {
    return children;
  }

  const isTextContent = type === CONTENT_TYPE_TEXT;

  // Text: copy button appears below message on hover
  if (isTextContent) {
    return (
      <div className={`group ${className}`}>
        {children}
        <div className="flex items-center gap-0.5 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {showCopy && (
            <button
              type="button"
              onClick={handleCopy}
              className="flex items-center justify-center rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
              title={copied ? 'Copied' : 'Copy'}
            >
              {copied ? <Check className="h-3.5 w-3.5 text-primary" /> : <Copy className="h-3.5 w-3.5" />}
            </button>
          )}
        </div>
      </div>
    );
  }

  // Image / website: action buttons float top-right, dark pill style
  return (
    <div className={`group relative ${className}`}>
      {children}
      <div className="absolute right-2 top-2 z-10 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        {showDownload && (
          <button
            type="button"
            onClick={handleDownload}
            title="Download"
            className="flex h-7 w-7 items-center justify-center rounded-full bg-black/60 text-white hover:bg-black/80 transition-colors"
          >
            <Download className="h-3.5 w-3.5" />
          </button>
        )}
        {showOpenInNewTab && (
          <button
            type="button"
            onClick={handleOpenInNewTab}
            title="Open in new tab"
            className="flex h-7 w-7 items-center justify-center rounded-full bg-black/60 text-white hover:bg-black/80 transition-colors"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
    </div>
  );
}