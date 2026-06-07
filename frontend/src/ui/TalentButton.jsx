import TalentIcon from './TalentIcon';

const BTN_W = 40;
const BTN_H = 52;

export default function TalentButton({
  talentId,
  iconIndex,
  name,
  currentLevel,
  maxPoints,
  pointsAvailable,
  locked,
  onInfo,
}) {
  const canUpgrade = !locked && currentLevel < maxPoints && pointsAvailable > 0;
  const frameCol = Math.min(maxPoints - 1, 2);
  const fillRatio = currentLevel / Math.max(maxPoints, 1);

  return (
    <button
      className={`talent-btn ${locked ? 'locked' : ''} ${currentLevel > 0 ? 'has-pts' : ''}`}
      title={name}
      onClick={() => onInfo?.(talentId, name, currentLevel, maxPoints, canUpgrade)}
      style={{
        width: BTN_W,
        height: BTN_H,
        backgroundImage: 'url(/assets/talent_button.png)',
        backgroundPosition: `-${frameCol * BTN_W}px 0`,
        backgroundSize: `${3 * BTN_W}px ${BTN_H}px`,
        imageRendering: 'pixelated',
        opacity: locked ? 0.4 : 1,
        position: 'relative',
        border: 'none',
        cursor: locked ? 'default' : 'pointer',
        padding: 0,
        flexShrink: 0,
      }}
    >
      <div style={{ position: 'absolute', top: 4, left: 4 }}>
        <TalentIcon talentId={talentId} iconIndex={iconIndex} alpha={locked ? 0.5 : 1} />
      </div>
      <div
        className="talent-fill"
        style={{
          position: 'absolute',
          bottom: 4,
          left: 4,
          width: `${fillRatio * 32}px`,
          height: 10,
          background: locked ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.27)',
          borderRadius: 0,
        }}
      />
    </button>
  );
}
