const PREP_TIERS = [
  { min: 1.0, label: 'Tier 0', dmg: '+10%' },
  { min: 3.0, label: 'Tier 1', dmg: '+20%' },
  { min: 5.0, label: 'Tier 2', dmg: '+35%' },
  { min: 9.0, label: 'Tier 3', dmg: '+50%' },
];

export default function PrepStrikeButton({
  subclass,
  invisible,
  prepSeconds,
  onPrepStrike,
}) {
  if (subclass !== 'assassin' || !invisible || !prepSeconds || prepSeconds < 1.0) {
    return null;
  }

  let tier = -1;
  for (let i = PREP_TIERS.length - 1; i >= 0; i--) {
    if (prepSeconds >= PREP_TIERS[i].min) { tier = i; break; }
  }

  const info = tier >= 0 ? PREP_TIERS[tier] : null;

  return (
    <div className="prep-btn-container">
      <button
        type="button"
        className="prep-btn"
        onClick={() => onPrepStrike?.()}
        title={`Preparation ${info?.label || '?'} — ${info?.dmg || '?'} damage (${Math.round(prepSeconds)}s)`}
      >
        <div className="prep-btn-label">
          Prep Strike
          {info && <span className="prep-btn-tier"> {info.label}</span>}
        </div>
        <div className="prep-btn-bar">
          <div className="prep-btn-fill" style={{
            width: `${Math.min(100, (prepSeconds / 9) * 100)}%`
          }} />
        </div>
      </button>
    </div>
  );
}
