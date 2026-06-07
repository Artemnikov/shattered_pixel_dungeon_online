/**
 * Client <-> server WebSocket contract.
 *
 * The entity shapes (Player, Mob, every item variant) are auto-generated from the
 * backend Pydantic models into ./generated/entities.ts -- regenerate with
 * `npm run gen:types` whenever those models change.
 *
 * This file hand-writes the parts that are NOT Pydantic models: the message
 * envelopes (INIT / STATE_UPDATE), the per-tick event payloads, and the outgoing
 * client messages. Those are assembled as plain dicts in backend/app/main.py,
 * engine/game/*.py and engine/game/serialization.py, so they have no schema to
 * generate from and must be kept in sync by hand.
 */
import type {
  Player,
  Mob,
  MeleeWeapon,
  Dagger,
  Bow,
  Staff,
  MissileWeapon,
  Armor,
  Ring,
  Artifact,
  Wand,
  HealthPotion,
  RevivingPotion,
  FuryPotion,
  Potion,
  Scroll,
  WornShortsword,
  BrokenSeal,
  ScrollOfRage,
  Gold,
  Food,
  MysteryMeat,
  Key,
  Seed,
  Stone,
  Boomerang,
  ThrowableDagger,
  Throwable,
  VelvetPouch,
  ScrollHolder,
  MagicalHolster,
  PotionBandolier,
  Bag,
} from './generated/entities';

export type { Player, Mob } from './generated/entities';

/** A grid cell coordinate pair `[x, y]` as sent in `visible_tiles` / `open_doors`. */
export type Vec2 = [number, number];

// --- items -----------------------------------------------------------------

/** The `AnyItem` discriminated union (on `kind`), mirroring base.py's AnyItem. */
export type GeneratedItem =
  | MeleeWeapon
  | Dagger
  | WornShortsword
  | Bow
  | Staff
  | MissileWeapon
  | Armor
  | Ring
  | Artifact
  | BrokenSeal
  | Wand
  | HealthPotion
  | RevivingPotion
  | FuryPotion
  | Potion
  | Scroll
  | ScrollOfRage
  | Gold
  | Food
  | MysteryMeat
  | Key
  | Seed
  | Stone
  | Boomerang
  | ThrowableDagger
  | Throwable
  | VelvetPouch
  | ScrollHolder
  | MagicalHolster
  | PotionBandolier
  | Bag;

/**
 * Fields the server attaches during serialization (serialization.py) that are not
 * on the Pydantic item models: the per-player action menu, and the per-run
 * colour/rune sprite for potions/scrolls.
 */
export interface SerializationExtras {
  actions: string[];
  default_action: string | null;
  description: string;
  /** Sprite cell for a potion/scroll's per-run appearance; only on those kinds. */
  appearance?: { col: number; row: number };
}

/** An item as it actually arrives over the wire (model + serialization extras). */
export type SerializedItem = GeneratedItem & SerializationExtras;

// --- shared small shapes ---------------------------------------------------

export type Difficulty = 'normal' | 'easy' | 'hard';

export type Direction =
  | 'UP'
  | 'DOWN'
  | 'LEFT'
  | 'RIGHT'
  | 'UP_LEFT'
  | 'UP_RIGHT'
  | 'DOWN_LEFT'
  | 'DOWN_RIGHT';

export interface TrapInfo {
  x: number;
  y: number;
  trap_type: string;
}

/** A single tile mutation in a MAP_PATCH event. */
export interface TilePatch {
  x: number;
  y: number;
  tile: number;
}

// --- server -> client: events ----------------------------------------------
// Payloads mirror the add_event(...) call sites across engine/game/*.py and
// engine/entities/item_actions.py.

export interface AttackEvent {
  type: 'ATTACK';
  data: {
    source: string;
    target: string;
    damage: number;
    surprise: boolean;
    crit: boolean;
    grim_proc: boolean;
  };
}

export interface MissEvent {
  type: 'MISS';
  data: { source: string; target: string; defense_verb: string };
}

export interface DamageEvent {
  type: 'DAMAGE';
  data: {
    target: string;
    amount: number;
    crit?: boolean;
    grim_proc?: boolean;
    bleed?: boolean;
  };
}

export interface DeathEvent {
  type: 'DEATH';
  data: { target: string };
}

export interface MoveEvent {
  type: 'MOVE';
  data: { entity: string; x: number; y: number };
}

export interface RangedAttackEvent {
  type: 'RANGED_ATTACK';
  data: {
    source: string;
    x: number;
    y: number;
    target_x: number;
    target_y: number;
    projectile: string;
    crit: boolean;
    grim_proc: boolean;
    /** Serialized thrown item, present for thrown inventory items (not wands). */
    item?: SerializedItem;
  };
}

export interface PlaySoundEvent {
  type: 'PLAY_SOUND';
  data: { sound: string };
}

export interface SearchEvent {
  type: 'SEARCH';
  data: {
    player: string;
    x: number;
    y: number;
    cells: Vec2[];
    revealed_tiles: number;
  };
}

export interface HealEvent {
  type: 'HEAL';
  data: { target: string; amount: number; x: number; y: number };
}

export interface TrapTriggeredEvent {
  type: 'TRAP_TRIGGERED';
  data: { player: string; trap: string; damage: number };
}

export interface DrinkEvent {
  type: 'DRINK';
  data: { player: string; type: string };
}

export interface ReadEvent {
  type: 'READ';
  data: { player: string; item: string };
}

export interface MapPatchEvent {
  type: 'MAP_PATCH';
  data: { tiles: TilePatch[] };
}

export interface PickupEvent {
  type: 'PICKUP';
  data: { player: string; item: string };
}

export interface DropEvent {
  type: 'DROP';
  data: { player: string; item: string };
}

export interface StairsDownEvent {
  type: 'STAIRS_DOWN';
  data: { player: string };
}

export interface StairsUpEvent {
  type: 'STAIRS_UP';
  data: { player: string };
}

export interface ReviveEvent {
  type: 'REVIVE';
  data: { target: string; source: string };
}

export interface UnlockEvent {
  type: 'UNLOCK';
  data: { player: string; x: number; y: number };
}

export interface LevelUpEvent {
  type: 'LEVEL_UP';
  data: {
    player: string;
    level: number;
    tier_unlocked?: number | null;
    talent_points?: Record<string, number>;
    can_choose_subclass: boolean;
    can_choose_armor_ability: boolean;
  };
}

export interface SubclassChoiceAvailableEvent {
  type: 'SUBCLASS_CHOICE_AVAILABLE';
  data: { player: string; options: string[] };
}

export interface ArmorAbilityChoiceAvailableEvent {
  type: 'ARMOR_ABILITY_CHOICE_AVAILABLE';
  data: { player: string; options: string[] };
}

export interface SubclassChosenEvent {
  type: 'SUBCLASS_CHOSEN';
  data: { player: string; subclass: string };
}

export interface TalentUpgradedEvent {
  type: 'TALENT_UPGRADED';
  data: { player: string; talent: string; level: number };
}

export interface ComboUpdateEvent {
  type: 'COMBO_UPDATE';
  data: { player: string; count: number };
}

export interface ComboMoveUnlockedEvent {
  type: 'COMBO_MOVE_UNLOCKED';
  data: { player: string; move: string };
}

export interface BerserkActivatedEvent {
  type: 'BERSERK_ACTIVATED';
  data: { player: string };
}

export interface RageChangedEvent {
  type: 'RAGE_CHANGED';
  data: { player: string; power: number };
}

export interface AffixSealEvent {
  type: 'AFFIX_SEAL';
  data: { player: string; armor: string };
}

/** Rogue: Cloak of Shadows stealth toggled on/off. */
export interface StealthEvent {
  type: 'STEALTH';
  data: { player: string; active: boolean };
}

/** Rogue: an enemy was Death-Marked. */
export interface DeathMarkEvent {
  type: 'DEATH_MARK';
  data: { player: string; target: string };
}

/** Rogue: a Shadow Clone ally was summoned. */
export interface ShadowCloneEvent {
  type: 'SHADOW_CLONE';
  data: { player: string; clone: string; x: number; y: number };
}

/** A shielding/barrier amount was granted to a player. */
export interface ShieldEvent {
  type: 'SHIELD';
  data: { player: string; amount: number };
}

/** Every event the server can place in `STATE_UPDATE.events`. */
export type GameEvent =
  | AttackEvent
  | MissEvent
  | DamageEvent
  | DeathEvent
  | MoveEvent
  | RangedAttackEvent
  | PlaySoundEvent
  | SearchEvent
  | HealEvent
  | TrapTriggeredEvent
  | DrinkEvent
  | ReadEvent
  | MapPatchEvent
  | PickupEvent
  | DropEvent
  | StairsDownEvent
  | StairsUpEvent
  | ReviveEvent
  | UnlockEvent
  | LevelUpEvent
  | SubclassChosenEvent
  | TalentUpgradedEvent
  | ComboUpdateEvent
  | ComboMoveUnlockedEvent
  | BerserkActivatedEvent
  | RageChangedEvent
  | AffixSealEvent
  | StealthEvent
  | DeathMarkEvent
  | ShadowCloneEvent
  | ShieldEvent
  | SubclassChoiceAvailableEvent
  | ArmorAbilityChoiceAvailableEvent;

export type GameEventType = GameEvent['type'];

// --- server -> client: message envelopes -----------------------------------

/** Sent on connect and whenever the player changes floor (main.py:154). */
export interface InitMessage {
  type: 'INIT';
  depth: number;
  grid: number[][];
  width: number;
  height: number;
  traps: TrapInfo[];
  /** Only present on the very first INIT after connecting. */
  player_id?: string;
}

/** The 20Hz per-player snapshot (main.py:168). */
export interface StateUpdateMessage {
  type: 'STATE_UPDATE';
  depth: number;
  difficulty: Difficulty;
  players: Player[];
  mobs: Mob[];
  items: SerializedItem[];
  visible_tiles: Vec2[];
  traps: TrapInfo[];
  gold: number;
  energy: number;
  events: GameEvent[];
  /**
   * Read defensively by the client but not currently forwarded in STATE_UPDATE;
   * kept optional to document the consumer's guard.
   */
  open_doors?: Vec2[];
}

export interface PongMessage {
  type: 'PONG';
}

/** Any frame the client can receive. */
export type ServerMessage = InitMessage | StateUpdateMessage | PongMessage;

// --- client -> server: messages --------------------------------------------
// Mirrors the handlers in backend/app/main.py:211-293.

export type ClientMessage =
  | { type: 'PING' }
  | { type: 'MOVE'; direction: Direction }
  | { type: 'MOVE_INTENT'; dx: number; dy: number }
  | { type: 'MOVE_STOP' }
  | { type: 'MOVE_TO'; x: number; y: number }
  | {
      type: 'EXECUTE_ITEM_ACTION';
      item_id: string;
      action: string;
      target_x?: number;
      target_y?: number;
    }
  | { type: 'SET_QUICKSLOT'; index: number; item_id: string }
  | { type: 'USE_QUICKSLOT'; index: number; target_x?: number; target_y?: number }
  | { type: 'EQUIP_ITEM'; item_id: string }
  | { type: 'DROP_ITEM'; item_id: string }
  | { type: 'USE_ITEM'; item_id: string }
  | { type: 'RANGED_ATTACK'; item_id: string; target_x: number; target_y: number }
  | { type: 'CHANGE_DIFFICULTY'; difficulty: Difficulty }
  | { type: 'SEARCH' }
  | { type: 'WAIT' }
  | { type: 'CHOOSE_SUBCLASS'; subclass: string }
  | { type: 'UPGRADE_TALENT'; talent: string }
  | { type: 'USE_ARMOR_ABILITY'; ability: string; target_x?: number; target_y?: number }
  | { type: 'TRIGGER_BERSERK' }
  | { type: 'PREPARATION_STRIKE'; target_x: number; target_y: number };
