import { useMemo } from 'react';
import TalentButton from './TalentButton';

// Base stars per tier (without bonus): thresholds[t+1] - thresholds[t]
const REG_STARS = { 1: 5, 2: 6, 3: 8, 4: 10 };

export default function TalentTierPane({
  tier,
  talents,
  talentLevels,
  talentPoints,
  subclass,
  armorAbility,
  abilityTier4,
  onInfo,
}) {
  const ptsAvailable = talentPoints?.[tier] || 0;
  const ptsSpent = useMemo(() => {
    return talents.reduce((sum, t) => sum + (talentLevels?.[t.id] || 0), 0);
  }, [talents, talentLevels]);

  const regStars = REG_STARS[tier] || 3;
  const totStars = regStars;
  const openStars = Math.min(ptsAvailable, totStars - ptsSpent);

  function isTalentLocked(t) {
    if (t.subclass && t.subclass !== subclass) return true;
    if (t.tier === 4 && !t.subclass && abilityTier4) {
      let belongsToAbility = false;
      for (const talents of Object.values(abilityTier4)) {
        if (talents.includes(t.id)) { belongsToAbility = true; break; }
      }
      if (belongsToAbility) {
        for (const [ability, talents] of Object.entries(abilityTier4)) {
          if (talents.includes(t.id) && ability !== armorAbility) return true;
        }
      }
    }
    return false;
  }

  return (
    <div className="tier-pane">
      <div className="tier-pane-header">
        <div className="tier-title">Tier {tier}</div>
        <div className="tier-stars">
          {Array.from({ length: totStars }, (_, i) => {
            let cls = 'tier-star';
            if (i < openStars) cls += ' available';
            else if (i < openStars + ptsSpent) cls += ' spent';
            return <span key={i} className={cls} />;
          })}
        </div>
        {ptsAvailable > 0 && (
          <span className="tier-pts-badge">{ptsAvailable}</span>
        )}
      </div>
      <div className="tier-buttons">
        {talents.map((t) => {
          const locked = isTalentLocked(t);
          const currentLevel = talentLevels?.[t.id] || 0;
          return (
            <TalentButton
              key={t.id}
              talentId={t.id}
              name={t.name || t.id}
              currentLevel={currentLevel}
              maxPoints={t.max_pts}
              pointsAvailable={ptsAvailable}
              locked={locked}
              onInfo={onInfo}
            />
          );
        })}
      </div>
    </div>
  );
}
