/**
 * BrandMark — a stylised kurta/kameez silhouette, the signature
 * garment of South Asian dress. Used as the brand mark for Brandmate.
 *
 * Sizes: pass `size` in pixels. Tone: "primary" → mark only,
 * "accent" → gold-only, "duo" → mark body + gold neckline detail.
 */
export function BrandMark({ size = 20, tone = 'duo', className = '', strokeWidth = 1 }) {
  const body =
    tone === 'accent'  ? 'var(--mark-soft)' :
    tone === 'currentColor' ? 'currentColor' :
    'var(--mark)';
  const detail =
    tone === 'primary' ? body :
    tone === 'currentColor' ? 'currentColor' :
    'var(--mark-soft)';

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      className={className}
      aria-hidden="true"
    >
      {/* Kameez silhouette — A-line tunic with cap sleeves and a
          gently curved hem. Symmetric around x=12. */}
      <path
        d="
          M 10.6 3.6
          L 8.6 3.9
          L 4.6 7.8
          L 4.4 9.4
          L 7.0 10.0
          L 7.8 9.4
          L 4.6 20.6
          Q 12 22.6 19.4 20.6
          L 16.2 9.4
          L 17.0 10.0
          L 19.6 9.4
          L 19.4 7.8
          L 15.4 3.9
          L 13.4 3.6
          L 13.0 4.6
          L 12 7.8
          L 11.0 4.6
          Z
        "
        fill={body}
        stroke={body}
        strokeWidth={strokeWidth * 0.5}
        strokeLinejoin="round"
      />

      {/* V-neck inset — thin gold line tracing the neckline */}
      <path
        d="M 11 4.4 L 12 7.6 L 13 4.4"
        fill="none"
        stroke={detail}
        strokeWidth={strokeWidth * 0.9}
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.95"
      />

      {/* Embroidered placket — a vertical seam with two beads,
          the kind of zari/zardozi detail you see down a kurta front */}
      <line
        x1="12" y1="8.4" x2="12" y2="13.6"
        stroke={detail}
        strokeWidth={strokeWidth * 0.7}
        strokeLinecap="round"
        opacity="0.85"
      />
      <circle cx="12" cy="9.6" r="0.55" fill={detail} />
      <circle cx="12" cy="12.4" r="0.55" fill={detail} />
    </svg>
  );
}

export default BrandMark;
