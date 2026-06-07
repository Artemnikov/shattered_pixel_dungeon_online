import { useMemo } from 'react';
import TalentIcon from './TalentIcon';

const TALENT_DESC = {
  iron_will: 'Armor DR +2 per point',
  iron_stomach: 'Food heals +33% per point',
  restored_strength: '+1 max HP per upgrade spent',
  light_armor: 'Armor penalty reduced',
  berserk_restoration: 'Berserk heal on kill',
  deathless_fury: 'Berserk prevents death',
  enraged_catalyst: 'Take damage → berserk power',
  berserk_rush: 'Berserk gives speed burst',
  combo_shield: 'Combo grants shielding',
  combo_restoration: 'Combo heals on finisher',
  slow_combo: 'Combo timer decays slower',
  lethal_hit: 'Combo finishers crit',
  endless_rage: 'Berserk lasts longer',
  imposing_presence: 'Nearby enemies weakened',
  enhanced_combo: 'Combo max +2 per point',
  combo_surge: 'Fury at max combo',
  sub_atk: '+1 attack per point',
  sub_def: '+1 defense per point',
  risk_reward: 'Low HP = more damage',
  berserk_duration: 'Berserk lasts much longer',
  rampage: 'Kills stack damage buff',
  combo_aura: 'Combo deals AOE damage',
  savage_capacity: 'Combo max +2 per point',
  deadly_followup: 'After target = extra damage',
  cached_rations: 'Food gives shielding',
  thiefs_intuition: 'Detect secrets better',
  sucker_punch: 'Surprise attacks stun',
  protective_shadows: 'In shadow = DR bonus',
  mystical_meal: 'Food restores wand charge',
  inscribed_stealth: 'Stealth on scroll read',
  wide_search: 'Search reveals more',
  silent_steps: "Moving doesn't break stealth",
  rogues_foresight: 'See traps from further',
  enhanced_rings: 'Ring effects +20%',
  light_cloak: 'Cloak recharges faster',
  enhanced_lethality: 'Assassinate deals more',
  assassins_reach: 'Assassinate from range',
  bounty_hunter: 'Kills drop more gold',
  evasive_armor: "Armor doesn't hinder dodge",
  projectile_momentum: 'Ranged damage ramps',
  speedy_stealth: 'Fast while stealthed',
  hasty_retreat: 'Smoke Bomb = speed boost',
  body_replacement: 'Swap with clone on death',
  shadow_step: 'Teleport to clone',
  fear_the_reaper: 'Death Mark instakills',
  deathly_durability: 'Death Mark target weakened',
  double_mark: 'Mark two enemies',
  shadow_blade: 'Clone deals more damage',
  cloned_armor: 'Clone has your armor',
  perfect_copy: 'Clone uses items',
  empowering_meal: 'Food gives strength buff',
  scholars_intuition: 'Identify items faster',
  lingering_magic: 'Potion effects last longer',
  backup_barrier: 'Potion gives shield',
  energizing_meal: 'Food restores energy',
  inscribed_power: 'Scroll gives shielding',
  wand_preservation: 'Wand save charge chance',
  arcane_vision: 'See magic traps',
  shield_battery: 'Wand use gives shield',
  desperate_power: 'Low HP = free wand charge',
  ally_warp: 'Swap places with ally',
  empowered_strike: 'Mage staff deals more',
  mystical_charge: 'Wand hits charge staff',
  excess_charge: 'Overcharge deals bonus',
  soul_eater: 'Kills heal',
  soul_siphon: 'Life drain on hit',
  necromancers_minions: 'Kills raise minions',
  natures_bounty: 'More dew & seeds',
  survivalists_intuition: 'Identify plants faster',
  followup_strike: 'Ranged→melee bonus',
  natures_aid: 'Dew drops heal more',
  invigorating_meal: 'Food = speed boost',
  liquid_nature: 'Water heals more',
  rejuvenating_steps: 'Walk in grass heals',
  heightened_senses: 'See hidden doors',
  durable_projectiles: 'Missiles break less',
  point_blank: 'Ranged deals more close',
  seer_shot: 'Reveal enemy on hit',
  farsight: '+1 view distance per point',
  shared_enchantment: 'Ranged gets weapon enchant',
  shared_upgrades: 'Ranged gets weapon upgrade',
  durable_tips: 'Missiles never break',
  barkskin: 'Grass gives armor buff',
  shielding_dew: 'Dew drops give shield',
  fan_of_blades: 'Blades hit multiple',
  projecting_blades: 'Blades go through walls',
  spirit_blades: 'Blades return to owner',
  growing_power: "Nature's Power grows",
  natures_wrath: 'Nature damage over time',
  wild_momentum: "Nature's Power = speed",
  eagle_eye: 'Hawk reveals map',
  go_for_the_eyes: 'Hawk blinds enemies',
  swift_spirit: 'Hawk attacks faster',
};

export default function WndInfoTalent({
  talentId,
  name,
  currentLevel,
  maxPoints,
  canUpgrade,
  onUpgrade,
  onClose,
}) {
  const desc = useMemo(() => TALENT_DESC[talentId] || '', [talentId]);
  const atMax = currentLevel >= maxPoints;

  return (
    <div className="wnd-overlay" onClick={onClose}>
      <div className="wnd-info-talent" onClick={(e) => e.stopPropagation()}>
        <div className="wnd-info-title">
          <TalentIcon talentId={talentId} />
          <span className="wnd-info-name">{name || talentId}</span>
          {currentLevel > 0 && <span className="wnd-info-level">+{currentLevel}</span>}
        </div>
        <div className="wnd-info-desc">{desc}</div>
        <div className="wnd-info-points">
          Points: {currentLevel}/{maxPoints}
        </div>
        <div className="wnd-info-actions">
          {canUpgrade ? (
            <button className="wnd-upgrade-btn" onClick={() => { onUpgrade?.(talentId); onClose?.(); }}>
              Upgrade
            </button>
          ) : (
            <button className="wnd-upgrade-btn disabled" disabled>
              {atMax ? 'MAXED' : 'Locked'}
            </button>
          )}
          <button className="wnd-close-btn" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
