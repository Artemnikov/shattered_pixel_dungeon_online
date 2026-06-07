import { useState, useMemo, useCallback } from 'react';
import TalentTierPane from './TalentTierPane';
import WndInfoTalent from './WndInfoTalent';

const TIER_THRESHOLDS = [0, 2, 7, 13, 21, 31];
const MAX_TALENT_TIERS = 4;

function computeTiersAvailable(level, subclass, armorAbility, maxTiers) {
  let available = 1;
  while (available < MAX_TALENT_TIERS && level + 1 >= TIER_THRESHOLDS[available + 1]) {
    available++;
  }
  if (available > 2 && !subclass) available = 2;
  if (available > 3 && !armorAbility) available = 3;
  return Math.min(available, maxTiers);
}

const BLOCKER_MESSAGES = {
  1: { level: 7, text: 'Reach level 7 to unlock more talents' },
  2: { level: 13, text: 'Reach level 13 to unlock more talents' },
  3: { level: 21, text: 'Reach level 21 to unlock more talents' },
};

export default function TalentPane({
  talentDefs,
  talentLevels,
  talentPoints,
  level,
  subclass,
  armorAbility,
  abilityTier4,
  onUpgradeTalent,
  onChooseSubclass,
  onChooseArmorAbility,
  onClose,
  loading,
  error,
}) {
  const [info, setInfo] = useState(null);

  const sortedTiers = useMemo(() => {
    return Object.entries(talentDefs?.tiers || {})
      .sort(([a], [b]) => Number(a) - Number(b));
  }, [talentDefs]);

  const tiersAvailable = useMemo(() => {
    return computeTiersAvailable(level, subclass, armorAbility, sortedTiers.length);
  }, [level, subclass, armorAbility, sortedTiers.length]);

  const hasTalentPoints = useMemo(() => {
    return Object.values(talentPoints || {}).some(pts => pts > 0);
  }, [talentPoints]);

  const handleInfo = useCallback((talentId, name, currentLevel, maxPoints, canUpgrade) => {
    setInfo({ talentId, name, currentLevel, maxPoints, canUpgrade });
  }, []);

  const blockerMsg = tiersAvailable < sortedTiers.length
    ? BLOCKER_MESSAGES[tiersAvailable]
    : null;

  if (loading) {
    return (
      <div className="talent-overlay" onClick={onClose}>
        <div className="talent-pane" onClick={(e) => e.stopPropagation()}>
          <div className="talent-header">
            <h2 className="talent-title">Talents</h2>
            <button className="talent-close" onClick={onClose}>×</button>
          </div>
          <div className="talent-loading">Loading talent data...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="talent-overlay" onClick={onClose}>
        <div className="talent-pane" onClick={(e) => e.stopPropagation()}>
          <div className="talent-header">
            <h2 className="talent-title">Talents</h2>
            <button className="talent-close" onClick={onClose}>×</button>
          </div>
          <div className="talent-error">Failed to load talents: {error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="talent-overlay" onClick={onClose}>
      <div className="talent-pane" onClick={(e) => e.stopPropagation()}>
        <div className="talent-header">
          <h2 className="talent-title">Talents</h2>
          <span className="talent-level-badge">Lv.{level}</span>
          {subclass && (
            <span className="talent-badge subclass-badge" title="Tap to view subclass info">
              {subclass}
            </span>
          )}
          {armorAbility && (
            <span className="talent-badge ability-badge" title={armorAbility.replace(/_/g, ' ')}>
              {armorAbility.replace(/_/g, ' ')}
            </span>
          )}
          {!subclass && level >= 6 && (
            <button className="talent-action-btn" onClick={onChooseSubclass}>
              Choose Subclass
            </button>
          )}
          {subclass && !armorAbility && level >= 13 && (
            <button className="talent-action-btn" onClick={onChooseArmorAbility}>
              Choose Ability
            </button>
          )}
          {hasTalentPoints && (
            <span className="talent-pts-badge">
              {Object.entries(talentPoints || {})
                .filter(([, pts]) => pts > 0)
                .map(([tier, pts]) => (
                  <span key={tier} className="talent-tier-pts">T{tier}: {pts}</span>
                ))}
            </span>
          )}
          <button className="talent-close" onClick={onClose}>&times;</button>
        </div>

        <div className="talent-body">
          {sortedTiers.slice(0, tiersAvailable).map(([tierKey, tier], idx) => {
            const tierNum = Number(tierKey);
            const normalTalents = tier.talents.filter(t => !t.is_ability_selector);
            if (normalTalents.length === 0) return null;

            return (
              <div key={tierKey}>
                {idx > 0 && <div className="tier-separator" />}
                <TalentTierPane
                  tier={tierNum}
                  talents={normalTalents}
                  talentLevels={talentLevels}
                  talentPoints={talentPoints}
                  subclass={subclass}
                  armorAbility={armorAbility}
                  abilityTier4={abilityTier4}
                  onInfo={handleInfo}
                />
              </div>
            );
          })}

          {blockerMsg && (
            <>
              <div className="tier-separator" />
              <div className="tier-pane-blocker">
                <div className="tier-pane-blocker-text">{blockerMsg.text}</div>
              </div>
            </>
          )}
        </div>
      </div>

      {info && (
        <WndInfoTalent
          talentId={info.talentId}
          name={info.name}
          currentLevel={info.currentLevel}
          maxPoints={info.maxPoints}
          canUpgrade={info.canUpgrade}
          onUpgrade={onUpgradeTalent}
          onClose={() => setInfo(null)}
        />
      )}
    </div>
  );
}
