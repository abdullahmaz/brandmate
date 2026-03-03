import { useEffect, useRef, useState } from 'react';
import { Check, Copy, Download, ExternalLink } from 'lucide-react';
import { CONTENT_TYPE_TEXT, CONTENT_TYPE_IMAGE, CONTENT_TYPE_WEBSITE } from '../constants/toolTypes';
import { toast } from '@/hooks/use-toast';

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
        const res = await fetch(downloadUrl, { mode: 'cors' });
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = downloadFilename || 'image.png';
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
  const actionsEl = (
    <div className={`flex items-center gap-1 opacity-0 shadow-sm transition-opacity group-hover:opacity-100 focus-within:opacity-100 ${isTextContent ? 'flex-shrink-0 pt-0.5' : 'absolute right-2 top-2 z-10'}`}>
      {showCopy && (
        <button
          type="button"
          onClick={handleCopy}
          className="rounded-md bg-black/70 p-1.5 text-white hover:bg-black/85"
          title={copied ? 'Copied' : 'Copy'}
          aria-label={copied ? 'Copied' : 'Copy'}
        >
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
        </button>
      )}
      {showDownload && (
        <button
          type="button"
          onClick={handleDownload}
          className="rounded-md bg-black/70 p-1.5 text-white hover:bg-black/85"
          title="Download"
          aria-label="Download"
        >
          <Download className="h-3.5 w-3.5" />
        </button>
      )}
      {showOpenInNewTab && (
        <button
          type="button"
          onClick={handleOpenInNewTab}
          className="rounded-md bg-black/70 p-1.5 text-white hover:bg-black/85"
          title="Open in new tab"
          aria-label="Open in new tab"
        >
          <ExternalLink className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );

  if (isTextContent) {
    return (
      <div className={`group relative flex items-start gap-2 ${className}`}>
        <div className="min-w-0 flex-1">{children}</div>
        {actionsEl}
      </div>
    );
  }

  return (
    <div className={`group relative ${className}`}>
      {children}
      {actionsEl}
    </div>
  );
}
