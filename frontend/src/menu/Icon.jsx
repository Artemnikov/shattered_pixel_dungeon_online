// Crops a single icon out of the shared icons.png sheet (256x128).
// Frame coordinates taken from core/.../ui/Icons.java.
import iconsUrl from '../assets/pixel-dungeon/interfaces/icons.png';

const ICON_FRAMES = {
  ENTER:    { x: 0,   y: 0,  w: 16, h: 16 },
  GOLD:     { x: 17,  y: 0,  w: 17, h: 16 },
  RANKINGS: { x: 34,  y: 0,  w: 17, h: 16 },
  NEWS:     { x: 68,  y: 0,  w: 16, h: 15 },
  CHANGES:  { x: 85,  y: 0,  w: 15, h: 15 },
  PREFS:    { x: 102, y: 0,  w: 14, h: 14 },
  SHPX:     { x: 119, y: 0,  w: 16, h: 16 },
  JOURNAL:  { x: 136, y: 0,  w: 17, h: 15 },
  CHEVRON:  { x: 240, y: 16, w: 13, h: 10 },
  AUDIO:    { x: 64,  y: 16, w: 14, h: 14 },
  DISPLAY:  { x: 32,  y: 16, w: 16, h: 12 },
  CLOSE:    { x: 80,  y: 32, w: 11, h: 11 },
};

const SHEET_W = 256;
const SHEET_H = 128;

export default function Icon({ name, scale = 2, className = '', style = {} }) {
  const f = ICON_FRAMES[name];
  if (!f) return null;
  return (
    <span
      className={`opd-icon ${className}`}
      style={{
        display: 'inline-block',
        width: f.w * scale,
        height: f.h * scale,
        backgroundImage: `url(${iconsUrl})`,
        backgroundRepeat: 'no-repeat',
        backgroundSize: `${SHEET_W * scale}px ${SHEET_H * scale}px`,
        backgroundPosition: `-${f.x * scale}px -${f.y * scale}px`,
        imageRendering: 'pixelated',
        ...style,
      }}
    />
  );
}
