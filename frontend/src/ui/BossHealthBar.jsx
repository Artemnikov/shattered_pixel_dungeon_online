// Top-of-screen boss HP bar, shown while a boss (e.g. Goo) is alive on the floor.
// Mirrors the original SPD's BossHealthBar HUD element.
export default function BossHealthBar({ boss }) {
  if (!boss) return null;
  const pct = Math.max(0, Math.min(1, boss.maxHp > 0 ? boss.hp / boss.maxHp : 0));

  return (
    <div className="boss-health-bar">
      <div className="boss-health-bar__box">
        <div className="boss-health-bar__name">{boss.name}</div>
        <div className="boss-health-bar__track">
          <div className="boss-health-bar__fill" style={{ width: `${pct * 100}%` }} />
        </div>
      </div>
    </div>
  );
}
