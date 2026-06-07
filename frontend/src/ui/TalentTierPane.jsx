import { useState, useMemo, useCallback } from 'react';
import TalentButton from './TalentButton';
import WndOptions from './WndOptions';

export default function TalentTierPane({
  tier,
  talents,
  talentLevels,
  talentPoints,
  tierThresholds,
  bonusTalentPoints,
  subclass,
  armorAbility,
  abilityTier4,
  upgradedTalentId,
  onAnimationDone,
  onUpgradeTalent,
  onInfo,
  metamorphMode,
  onMetamorphChoose,
}) {
  const [showShuffle, setShowShuffle] = useState(false);

  const ptsAvailable = talentPoints?.[tier] || 0;
  const ptsSpent = useMemo(() => {
    return talents.reduce((sum, t) => sum + (talentLevels?.[t.id] || 0), 0);
  }, [talents, talentLevels]);

  const bonus = bonusTalentPoints?.[tier] || 0;
  const totStars = (tierThresholds[tier + 1] - tierThresholds[tier]) + bonus;
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

  const handleShuffleAll = useCallback(() => {
    let remaining = talentPoints?.[tier] || 0;
    let attempts = 0;
    while (remaining > 0 && attempts < 100) {
      const unlocked = talents.filter(t => {
        if (t.subclass && t.subclass !== subclass) return false;
        if (t.tier === 4 && !t.subclass && abilityTier4) {
          let ba = false;
          for (const tt of Object.values(abilityTier4)) { if (tt.includes(t.id)) { ba = true; break; } }
          if (ba) { for (const [a, tt] of Object.entries(abilityTier4)) { if (tt.includes(t.id) && a !== armorAbility) return false; } }
        }
        return (talentLevels?.[t.id] || 0) < t.max_pts;
      });
      if (unlocked.length === 0) break;
      const pick = unlocked[Math.floor(Math.random() * unlocked.length)];
      onUpgradeTalent?.(pick.id);
      remaining--;
      attempts++;
    }
  }, [tier, talents, talentLevels, talentPoints, onUpgradeTalent, subclass, armorAbility, abilityTier4]);

  const handleShuffleOne = useCallback(() => {
    const unlocked = talents.filter(t => {
      if (t.subclass && t.subclass !== subclass) return false;
      if (t.tier === 4 && !t.subclass && abilityTier4) {
        let ba = false;
        for (const tt of Object.values(abilityTier4)) { if (tt.includes(t.id)) { ba = true; break; } }
        if (ba) { for (const [a, tt] of Object.entries(abilityTier4)) { if (tt.includes(t.id) && a !== armorAbility) return false; } }
      }
      return (talentLevels?.[t.id] || 0) < t.max_pts;
    });
    if (unlocked.length === 0) return;
    const pick = unlocked[Math.floor(Math.random() * unlocked.length)];
    onUpgradeTalent?.(pick.id);
  }, [talents, talentLevels, onUpgradeTalent, subclass, armorAbility, abilityTier4]);

  return (
    <div className="tier-pane">
      {!metamorphMode && (
        <div className="tier-pane-header">
          <div className="tier-title">Tier {tier}</div>
          <div className="tier-stars">
            {Array.from({ length: totStars }, (_, i) => {
              let cls = 'tier-star';
              if (i < openStars) cls += ' available';
              else if (i < openStars + ptsSpent) cls += ' spent';
              else cls += ' locked';
              return (
                <div
                  key={i}
                  className={cls}
                  style={{
                    backgroundImage: 'url(/assets/speck_star.png)',
                    backgroundSize: '14px 14px',
                    imageRendering: 'pixelated',
                  }}
                />
              );
            })}
          </div>
          {ptsAvailable > 0 && (
            <span className="tier-pts-badge">{ptsAvailable}</span>
          )}
          {ptsAvailable > 0 && (
            <button
              className="tier-random-btn"
              title="Randomly assign talent points"
              onClick={() => setShowShuffle(true)}
            >
              ↻
            </button>
          )}
        </div>
      )}
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
              locked={locked || (metamorphMode && currentLevel === 0)}
              onInfo={onInfo}
              upgradedTalentId={upgradedTalentId}
              onAnimationDone={onAnimationDone}
              metamorphMode={metamorphMode}
              onMetamorphChoose={onMetamorphChoose}
            />
          );
        })}
      </div>

      {showShuffle && (
        <WndOptions
          icon="↻"
          title="Randomly assign talents"
          message="Choose how to assign remaining talent points for this tier."
          options={['Fill all', 'Fill one', 'Cancel']}
          onSelect={(idx) => {
            if (idx === 0) handleShuffleAll();
            else if (idx === 1) handleShuffleOne();
          }}
          onClose={() => setShowShuffle(false)}
        />
      )}
    </div>
  );
}
