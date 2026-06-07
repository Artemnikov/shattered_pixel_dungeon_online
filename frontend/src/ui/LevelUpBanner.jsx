import { useEffect, useRef } from 'react';

export default function LevelUpBanner({
  level,
  tierUnlocked,
  talentPoints,
  canChooseSubclass,
  canChooseArmorAbility,
  onOpenTalents,
  onDismiss,
}) {
  const timerRef = useRef(null);
  const onDismissRef = useRef(onDismiss);
  useEffect(() => { onDismissRef.current = onDismiss; });

  useEffect(() => {
    timerRef.current = setTimeout(() => onDismissRef.current?.(), 3000);
    return () => clearTimeout(timerRef.current);
  }, [level]);

  const handleClick = () => {
    clearTimeout(timerRef.current);
    const hasMilestone = tierUnlocked || canChooseSubclass || canChooseArmorAbility;
    if (hasMilestone) onOpenTalents?.();
    onDismiss?.();
  };

  const totalPts = Object.values(talentPoints || {}).reduce((a, b) => a + b, 0);
  const milestone = canChooseSubclass ? 'New subclass available!'
    : canChooseArmorAbility ? 'New armor ability available!'
    : tierUnlocked ? `Tier ${tierUnlocked} unlocked!`
    : null;

  return (
    <div className="levelup-banner" onClick={handleClick}>
      <div className="levelup-banner-content">
        <span className="levelup-text">Level {level}!</span>
        {milestone && <span className="levelup-milestone">{milestone}</span>}
        {totalPts > 0 && (
          <span className="levelup-pts">{totalPts} talent point{totalPts > 1 ? 's' : ''}</span>
        )}
        <span className="levelup-hint">Tap to view</span>
      </div>
    </div>
  );
}
