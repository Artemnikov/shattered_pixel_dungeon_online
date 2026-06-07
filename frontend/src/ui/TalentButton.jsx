import { useRef, useState, useEffect } from 'react';
import TalentIcon from './TalentIcon';
import AudioManager from '../audio/AudioManager';

const BTN_W = 40;
const BTN_H = 52;

const PARTICLE_STYLES = Array.from({ length: 12 }, (_, i) => {
  const angle = (Math.PI * 2 * i) / 12 + Math.random() * 0.3;
  const dist = 20 + Math.random() * 15;
  return {
    '--dx': `${Math.cos(angle) * dist}px`,
    '--dy': `${Math.sin(angle) * dist}px`,
    '--delay': `${Math.random() * 0.1}s`,
  };
});

export default function TalentButton({
  talentId,
  iconIndex,
  name,
  currentLevel,
  maxPoints,
  pointsAvailable,
  locked,
  onInfo,
  upgradedTalentId,
  onAnimationDone,
  metamorphMode,
  onMetamorphChoose,
}) {
  const canUpgrade = !locked && currentLevel < maxPoints && pointsAvailable > 0;
  const frameCol = maxPoints - 1;
  const fillRatio = currentLevel / Math.max(maxPoints, 1);
  const btnRef = useRef(null);
  const [pressed, setPressed] = useState(false);
  const [burstKey, setBurstKey] = useState(0);

  // Trigger burst when upgradedTalentId matches this talent (SPD-style particle effect)
  useEffect(() => {
    if (upgradedTalentId === talentId && !locked) {
      AudioManager.play('LEVELUP', 1.2);
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setBurstKey(k => k + 1);
    }
  }, [upgradedTalentId, talentId, locked]);

  useEffect(() => {
    if (burstKey === 0) return;
    const timer = setTimeout(() => {
      onAnimationDone?.();
    }, 500);
    return () => clearTimeout(timer);
  }, [burstKey, onAnimationDone]);

  const handlePointerDown = () => {
    if (locked) return;
    setPressed(true);
    AudioManager.play('CLICK');
  };
  const handlePointerUp = () => setPressed(false);

  return (
    <button
      ref={btnRef}
      className={`talent-btn ${locked ? 'locked' : ''} ${currentLevel > 0 ? 'has-pts' : ''} ${pressed ? 'pressed' : ''} ${metamorphMode && currentLevel > 0 ? 'metamorph-target' : ''}`}
      title={name}
      onClick={() => {
        if (metamorphMode) {
          onMetamorphChoose?.(talentId);
        } else {
          onInfo?.(talentId, name, currentLevel, maxPoints, canUpgrade);
        }
      }}
      onMouseDown={handlePointerDown}
      onMouseUp={handlePointerUp}
      onMouseLeave={handlePointerUp}
      onTouchStart={handlePointerDown}
      onTouchEnd={handlePointerUp}
      style={{
        width: BTN_W,
        height: BTN_H,
        backgroundImage: 'url(/assets/talent_button.png)',
        backgroundPosition: `-${frameCol * BTN_W}px 0`,
        backgroundSize: `${4 * BTN_W}px ${BTN_H}px`,
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
          bottom: 14,
          left: 4,
          width: `${fillRatio * 32}px`,
          height: 10,
          background: locked ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.27)',
          borderRadius: 0,
        }}
      />
      {burstKey > 0 && (
        <div className="talent-burst" key={burstKey}>
          {PARTICLE_STYLES.map((s, i) => (
            <div
              key={i}
              className="talent-star-particle"
              style={{
                '--dx': s['--dx'],
                '--dy': s['--dy'],
                '--delay': s['--delay'],
              }}
            />
          ))}
        </div>
      )}
    </button>
  );
}
