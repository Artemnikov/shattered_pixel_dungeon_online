import { useState } from 'react';
import { getHeroIconIndex } from '../data/heroIcons';
import HeroIcon from './HeroIcon';

const SUBCLASS_SHORT_DESC = {
  berserker: 'A furious warrior who channels rage',
  gladiator: 'Master of combat who builds momentum',
  assassin: 'A deadly shadow who strikes from darkness',
  freerunner: 'An agile rogue who moves freely',
  battlemage: 'Mage who channels magic through staff',
  warlock: 'Mage who drains life from enemies',
  sniper: 'Huntress who picks off enemies from afar',
  warden: 'Huntress who draws power from nature',
};

const SUBCLASS_FULL_DESC = {
  berserker: 'A furious warrior who channels rage into devastating power. Unlocks rage mechanics and berserk transformation. The berserker grows stronger as they take damage, eventually entering a state of uncontrollable fury.',
  gladiator: 'A master of combat who builds momentum through consecutive hits. Unlocks combo system with escalating finishers. Each hit builds combo power, unlocking devastating special moves at higher combo counts.',
  assassin: 'A deadly shadow who strikes from darkness with lethal precision. Bonuses to surprise attacks and stealth. Preparation time increases assassination damage dramatically.',
  freerunner: 'An agile rogue who moves freely through the dungeon. Enhanced mobility, evasion, and stealth. Projectile momentum builds with movement speed.',
  battlemage: 'A mage who channels magic through their staff in melee combat. Empowered strikes and staff charges. Each wand hit empowers the staff for devastating melee attacks.',
  warlock: 'A mage who drains life from enemies to sustain themselves. Soul eating, lifesteal, and necromancy. Kills restore health and raise minions to fight alongside you.',
  sniper: 'A huntress who picks off enemies from afar with precision. Enhanced ranged attacks and vision. Shared enchantments and upgrades make the bow deadly at any range.',
  warden: 'A huntress who draws power from nature and the dungeon\'s flora. Herbology, barkskin, and nature magic. Grass and dew provide healing, shielding, and armor.',
};

export default function SubclassChoice({ options, onChoose, onSkip }) {
  const [confirm, setConfirm] = useState(null);
  const [info, setInfo] = useState(null);

  if (!options || options.length === 0) return null;

  if (confirm) {
    return (
      <div className="choice-overlay" onClick={() => setConfirm(null)}>
        <div className="wnd-options" onClick={(e) => e.stopPropagation()}>
          <div className="wnd-options-icon">
            <HeroIcon index={getHeroIconIndex('subclass', confirm)} size={32} />
          </div>
          <div className="wnd-options-title">
            {confirm.charAt(0).toUpperCase() + confirm.slice(1)}
          </div>
          <div className="wnd-options-msg">Are you sure you want to choose this subclass?</div>
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
    return (
      <div className="choice-overlay" onClick={() => setInfo(null)}>
        <div className="wnd-info-subclass" onClick={(e) => e.stopPropagation()}>
          <div className="wnd-info-title">
            <HeroIcon index={getHeroIconIndex('subclass', info)} size={32} />
            <span className="wnd-info-name">{info.charAt(0).toUpperCase() + info.slice(1)}</span>
          </div>
          <div className="wnd-info-desc">{SUBCLASS_FULL_DESC[info] || ''}</div>
          <button className="wnd-close-btn" onClick={() => setInfo(null)}>Close</button>
        </div>
      </div>
    );
  }

  return (
    <div className="choice-overlay" onClick={onSkip}>
      <div className="choice-modal wnd-choose-subclass" onClick={(e) => e.stopPropagation()}>
        <div className="choice-header">
          <span className="choice-header-icon">⚔</span>
          <span className="choice-header-title">Choose a Subclass</span>
        </div>
        <p className="choice-subtitle">You have reached level 6. Choose your path.</p>
        <div className="choice-list">
          {options.map(sc => (
            <div key={sc} className="choice-list-item">
              <button
                className="choice-list-btn"
                onClick={() => setConfirm(sc)}
              >
                <span className="choice-list-name">{sc.charAt(0).toUpperCase() + sc.slice(1)}</span>
                <span className="choice-list-desc">{SUBCLASS_SHORT_DESC[sc] || ''}</span>
              </button>
              <button
                className="choice-info-btn"
                title="Info"
                onClick={() => setInfo(sc)}
              >
                ?
              </button>
            </div>
          ))}
        </div>
        <button className="choice-skip" onClick={onSkip}>
          Decide later (press T to open talents)
        </button>
      </div>
    </div>
  );
}
