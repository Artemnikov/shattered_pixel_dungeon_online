import { useState } from 'react';
import { getHeroIconIndex } from '../data/heroIcons';
import HeroIcon from './HeroIcon';

const ABILITY_TO_NAME = {
  heroic_leap: 'Heroic Leap',
  shockwave: 'Shockwave',
  endure: 'Endure',
  smoke_bomb: 'Smoke Bomb',
  death_mark: 'Death Mark',
  shadow_clone: 'Shadow Clone',
  elemental_blast: 'Elemental Blast',
  wild_magic: 'Wild Magic',
  warp_beacon: 'Warp Beacon',
  spectral_blades: 'Spectral Blades',
  natures_power: "Nature's Power",
  spirit_hawk: 'Spirit Hawk',
};

const ABILITY_SHORT_DESC = {
  heroic_leap: 'Leap and slam, damaging and stunning',
  shockwave: 'Unleash a powerful shockwave',
  endure: 'Reduce all damage taken temporarily',
  smoke_bomb: 'Blind enemies and escape',
  death_mark: 'Mark an enemy for bonus damage',
  shadow_clone: 'Create a phantom copy of yourself',
  elemental_blast: 'Unleash elemental energy around you',
  wild_magic: 'Channel unpredictable magic',
  warp_beacon: 'Place and recall to a beacon',
  spectral_blades: 'Hurl ethereal blades through enemies',
  natures_power: 'Draw power from the earth',
  spirit_hawk: 'Summon a spirit hawk to scout',
};

function talentIdToAbility(tid) {
  return tid.replace(/_(talent|ability)$/, '');
}

export default function ArmorAbilityChoice({ options, onChoose, onSkip, abilitySelectors }) {
  const [confirm, setConfirm] = useState(null);
  const [info, setInfo] = useState(null);

  if (!options || options.length === 0) return null;

  const confirmAbility = abilitySelectors?.[confirm] || talentIdToAbility(confirm || '');

  if (confirm) {
    return (
      <div className="choice-overlay" onClick={() => setConfirm(null)}>
        <div className="wnd-options" onClick={(e) => e.stopPropagation()}>
          <div className="wnd-options-icon">
            <HeroIcon index={getHeroIconIndex('ability', confirmAbility)} size={32} />
          </div>
          <div className="wnd-options-title">
            {ABILITY_TO_NAME[confirmAbility] || confirmAbility.replace(/_/g, ' ')}
          </div>
          <div className="wnd-options-msg">Are you sure you want to choose this ability?</div>
          <div className="wnd-options-buttons">
            <button className="wnd-opt-btn yes" onClick={() => { onChoose(confirm); setConfirm(null); }}>
              Yes
            </button>
            <button className="wnd-opt-btn no" onClick={() => setConfirm(null)}>
              No
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (info) {
    const infoAbility = abilitySelectors?.[info] || talentIdToAbility(info || '');
    return (
      <div className="choice-overlay" onClick={() => setInfo(null)}>
        <div className="wnd-info-ability" onClick={(e) => e.stopPropagation()}>
          <div className="wnd-info-title">
            <HeroIcon index={getHeroIconIndex('ability', infoAbility)} size={32} />
            <span className="wnd-info-name">{ABILITY_TO_NAME[infoAbility] || infoAbility}</span>
          </div>
          <div className="wnd-info-desc">{ABILITY_SHORT_DESC[infoAbility] || ''}</div>
          <button className="wnd-close-btn" onClick={() => setInfo(null)}>Close</button>
        </div>
      </div>
    );
  }

  return (
    <div className="choice-overlay" onClick={onSkip}>
      <div className="choice-modal wnd-choose-armor-ability" onClick={(e) => e.stopPropagation()}>
        <div className="choice-header">
          <span className="choice-header-icon">🛡</span>
          <span className="choice-header-title">Choose an Armor Ability</span>
        </div>
        <p className="choice-subtitle">You have reached level 13. Imbue your armor with a powerful ability.</p>
        <div className="choice-list">
          {options.map(tid => {
            const ability = abilitySelectors?.[tid] || talentIdToAbility(tid);
            return (
              <div key={tid} className="choice-list-item">
                <button
                  className="choice-list-btn"
                  onClick={() => setConfirm(tid)}
                >
                  <span className="choice-list-name">{ABILITY_TO_NAME[ability] || ability.replace(/_/g, ' ')}</span>
                  <span className="choice-list-desc">{ABILITY_SHORT_DESC[ability] || ''}</span>
                </button>
                <button
                  className="choice-info-btn"
                  title="Info"
                  onClick={() => setInfo(tid)}
                >
                  ?
                </button>
              </div>
            );
          })}
        </div>
        <button className="choice-skip" onClick={onSkip}>
          Decide later (press T to open talents)
        </button>
      </div>
    </div>
  );
}
