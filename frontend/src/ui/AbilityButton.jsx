const ABILITY_LABELS = {
  heroic_leap: 'Heroic Leap',
  shockwave: 'Shockwave',
  endure: 'Endure',
  smoke_bomb: 'Smoke Bomb',
  death_mark: 'Death Mark',
  shadow_clone: 'Shadow Clone',
};

const ABILITY_COSTS = {
  heroic_leap: 30,
  shockwave: 30,
  endure: 15,
  smoke_bomb: 50,
  death_mark: 25,
  shadow_clone: 35,
};

export default function AbilityButton({
  armorAbility,
  armorCharge,
  onUseAbility,
}) {
  const label = ABILITY_LABELS[armorAbility] || armorAbility;
  const cost = ABILITY_COSTS[armorAbility] || 30;
  const pct = Math.min(1, armorCharge / (cost || 1));

  if (!armorAbility) return null;

  return (
    <div className="ability-btn-container">
      <button
        type="button"
        className={`ability-btn ${pct >= 1 ? 'ability-btn-ready' : ''}`}
        onClick={() => onUseAbility?.(armorAbility)}
        title={`${label} (${Math.round(pct * 100)}% charge)`}
      >
        <div className="ability-btn-label">{label}</div>
        <div className="ability-btn-charge-bar">
          <div className="ability-btn-charge-fill" style={{ width: `${pct * 100}%` }} />
        </div>
      </button>
    </div>
  );
}
