export default function RankingsPane({
  playerName,
  classType,
  level,
  depth,
  gold,
  subclass,
  armorAbility,
  talentLevels,
  talentDefs,
  inventory,
  onNewGame,
  onMenu,
}) {
  const score = depth * 100 + level * 50 + gold * 2;

  const ownedTalents = Object.entries(talentLevels || {})
    .filter(([, lvl]) => lvl > 0)
    .sort(([a], [b]) => {
      const ta = talentDefs?.tiers ? findTier(a, talentDefs) : 0;
      const tb = talentDefs?.tiers ? findTier(b, talentDefs) : 0;
      return (ta - tb) || a.localeCompare(b);
    });

  function findTier(tid, defs) {
    for (const [tk, tier] of Object.entries(defs.tiers || {})) {
      if (tier.talents.some(t => t.id === tid)) return Number(tk);
    }
    return 0;
  }

  function talentName(tid) {
    for (const [, tier] of Object.entries(talentDefs?.tiers || {})) {
      const found = tier.talents.find(t => t.id === tid);
      if (found) return found.name || tid;
    }
    return tid.replace(/_/g, ' ');
  }

  return (
    <div
      className="rankings-overlay"
      onClick={() => {}}
    >
      <div className="rankings-pane" onClick={e => e.stopPropagation()}>
        <h2 className="rankings-title">Rankings</h2>

        <div className="rankings-score">{score.toLocaleString()} pts</div>

        <div className="rankings-stats">
          <div className="rankings-stat-row">
            <span className="rankings-stat-label">Name</span>
            <span className="rankings-stat-value">{playerName}</span>
          </div>
          <div className="rankings-stat-row">
            <span className="rankings-stat-label">Class</span>
            <span className="rankings-stat-value">{classType} {subclass || ''}</span>
          </div>
          <div className="rankings-stat-row">
            <span className="rankings-stat-label">Depth</span>
            <span className="rankings-stat-value">{depth}</span>
          </div>
          <div className="rankings-stat-row">
            <span className="rankings-stat-label">Level</span>
            <span className="rankings-stat-value">{level}</span>
          </div>
          <div className="rankings-stat-row">
            <span className="rankings-stat-label">Gold</span>
            <span className="rankings-stat-value">{gold}</span>
          </div>
          {armorAbility && (
            <div className="rankings-stat-row">
              <span className="rankings-stat-label">Armor Ability</span>
              <span className="rankings-stat-value">{armorAbility.replace(/_/g, ' ')}</span>
            </div>
          )}
        </div>

        <h3 className="rankings-section-title">Talents</h3>
        <div className="rankings-talents">
          {ownedTalents.length === 0 && (
            <div className="rankings-empty">No talents acquired</div>
          )}
          {ownedTalents.map(([tid, lvl]) => (
            <div key={tid} className="rankings-talent-row">
              <span className="rankings-talent-name">{talentName(tid)}</span>
              <span className="rankings-talent-level">{'★'.repeat(lvl)}</span>
            </div>
          ))}
        </div>

        <h3 className="rankings-section-title">Items</h3>
        <div className="rankings-items">
          {(inventory || []).length === 0 && (
            <div className="rankings-empty">No items</div>
          )}
          {(inventory || []).slice(0, 20).map((item, i) => (
            <div key={i} className="rankings-item-row">
              {item.name}
            </div>
          ))}
        </div>

        <div className="rankings-buttons">
          <button className="rankings-btn" onClick={onNewGame}>New Game</button>
          <button className="rankings-btn" onClick={onMenu}>Menu</button>
        </div>
      </div>
    </div>
  );
}
