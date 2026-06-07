import { getTalentIconIndex } from '../data/talentIcons';

const ICON_SIZE = 32;
const COLS = 32;
const SHEET_W = 1024;
const SHEET_H = 256;

export default function TalentIcon({ talentId, iconIndex, className, alpha }) {
  const idx = iconIndex ?? getTalentIconIndex(talentId);
  const col = idx % COLS;
  const row = Math.floor(idx / COLS);

  return (
    <div
      className={`talent-icon ${className || ''}`}
      style={{
        width: ICON_SIZE,
        height: ICON_SIZE,
        backgroundImage: 'url(/assets/talent_icons.png)',
        backgroundPosition: `-${col * ICON_SIZE}px -${row * ICON_SIZE}px`,
        backgroundSize: `${SHEET_W}px ${SHEET_H}px`,
        imageRendering: 'pixelated',
        opacity: alpha ?? 1,
        flexShrink: 0,
      }}
    />
  );
}
