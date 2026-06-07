export default function BerserkButton({
  berserkPower,
  onTriggerBerserk,
}) {
  if (!berserkPower || berserkPower <= 0) return null;

  const pct = Math.min(1, berserkPower);
  const ready = berserkPower >= 1.0;

  return (
    <div className="berserk-btn-container">
      <button
        type="button"
        className={`berserk-btn ${ready ? 'berserk-btn-ready' : ''}`}
        onClick={() => ready && onTriggerBerserk?.()}
        disabled={!ready}
        title={ready ? 'Trigger Berserk!' : `Rage: ${Math.round(pct * 100)}%`}
      >
        <div className="berserk-btn-label">{ready ? 'BERSERK!' : 'Rage'}</div>
        <div className="berserk-btn-bar">
          <div className="berserk-btn-fill" style={{ width: `${pct * 100}%` }} />
        </div>
      </button>
    </div>
  );
}
