const COLS = 8;
const ICON_SIZE = 16;
const SHEET_W = 128;
const SHEET_H = 256;

export default function HeroIcon({ index, size, className }) {
  const s = size || ICON_SIZE;
  const col = index % COLS;
  const row = Math.floor(index / COLS);
  const scale = s / ICON_SIZE;

  return (
    <div
      className={`hero-icon ${className || ''}`}
      style={{
        width: s,
        height: s,
        backgroundImage: 'url(/assets/hero_icons.png)',
        backgroundPosition: `-${col * s}px -${row * s}px`,
        backgroundSize: `${SHEET_W * scale}px ${SHEET_H * scale}px`,
        imageRendering: 'pixelated',
        flexShrink: 0,
      }}
    />
  );
}
