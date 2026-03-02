import { Copy, Download, ExternalLink } from 'lucide-react';

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
}) {
  const handleCopy = async () => {
    if (type !== 'text' || copyContent == null) return;
    try {
      await navigator.clipboard.writeText(copyContent);
    } catch {
      // fallback for older browsers
      const ta = document.createElement('textarea');
      ta.value = copyContent;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
  };

  const handleDownload = () => {
    if (type === 'image' && downloadUrl) {
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = downloadFilename || 'image.png';
      a.target = '_blank';
      document.body.appendChild(a);
      a.click();
      a.remove();
    } else if (type === 'website' && downloadHtml) {
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
    if (type === 'website' && downloadHtml) {
      const blob = new Blob([downloadHtml], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank', 'noopener,noreferrer');
    }
  };

  const showCopy = type === 'text' && copyContent != null;
  const showDownload = (type === 'image' && downloadUrl) || (type === 'website' && downloadHtml);
  const showOpenInNewTab = type === 'website' && downloadHtml;

  if (!showCopy && !showDownload && !showOpenInNewTab) {
    return children;
  }

  return (
    <div className={`group relative ${className}`}>
      {children}
      <div className="absolute right-2 top-2 z-10 flex items-center gap-1 opacity-0 shadow-sm transition-opacity group-hover:opacity-100 focus-within:opacity-100">
        {showCopy && (
          <button
            type="button"
            onClick={handleCopy}
            className="rounded-md bg-black/70 p-1.5 text-white hover:bg-black/85"
            title="Copy"
            aria-label="Copy"
          >
            <Copy className="h-3.5 w-3.5" />
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
    </div>
  );
}
