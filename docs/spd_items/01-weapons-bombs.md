# SPD Weapons & Bombs Reference

Source: `core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/weapon/` and `items/bombs/`.
All formulas verbatim from Java source. `lvl` = enchant level (can be negative if cursed/degraded).

## 1. Melee Weapon Base Formulas (`MeleeWeapon.java` / `Weapon.java`)

- `min(lvl) = tier + lvl`
- `max(lvl) = 5*(tier+1) + lvl*(tier+1)`  (per-weapon overrides below)
- `STRReq(tier, lvl) = (8 + tier*2) - floor((sqrt(8*lvl+1)-1)/2)`  — i.e. STR drops by 1 at lvl +1, +3, +6, +10, +15... (triangular numbers). `masteryPotionBonus` subtracts an extra 2 if hero drank Potion of Mastery for this weapon.
- `encumbrance = STRReq() - STR()` (only if positive)
- `accuracyFactor = baseACC / 1.5^encumbrance` (if encumbrance>0)
- `delayFactor = baseDLY * 1.2^encumbrance` (if encumbrance>0), then `/ speedMultiplier` from Augment
- `reachFactor`: base 1, +1 if `Projecting` enchant, weapon RCH adds further

### Weapon.Augment enum
| Augment | Damage factor | Delay factor |
|---|---|---|
| NONE | x1.0 | x1.0 |
| SPEED | x0.7 | x2/3 (1.5x attack speed) |
| DAMAGE | x1.5 | x5/3 (0.6x attack speed) |

### Enchantment.random() — proc rarity table
`typeChances = [50, 40, 10]` → Common 50% total (12.5% each of 4), Uncommon 40% (6.67% each of 6), Rare 10% (3.33% each of 3).
- Common: Blazing, Chilling, Kinetic, Shocking
- Uncommon: Blocking, Blooming, Elastic, Lucky, Projecting, Unstable
- Rare: Corrupting, Grim, Vampiric
- Curses (separate pool): Annoying, Displacing, Dazzling, Explosive, Sacrificial, Wayward, Polarized, Friendly

### Item.random() generation chances
- Upgrade level: +0 75%, +1 20%, +2 5%
- 30% chance cursed (random curse enchant, `levelKnown=false`, glyph hidden)
- 10% chance enchanted (random non-curse enchant)

---

## 2. Melee Weapons by Tier

Drop weights from `Generator.java` `defaultProbs`.

### Tier 1 (`WEP_T1`, probs `{2,0,2,2,2,2}` for WornShortsword/MagesStaff/Dagger/Gloves/Rapier/Cudgel — MagesStaff prob 0, never random-drops)

| Weapon | STRReq(0) | ACC | DLY | RCH | max(lvl) formula | max(0) |
|---|---|---|---|---|---|---|
| WornShortsword | 10 | 1.0 | 1.0 | 1 | base: `5*(t+1)+lvl*(t+1)` = 10+2lvl | 10 |
| Dagger | 10 | 1.0 | 1.0 | 1 | `4*(t+1)+lvl*(t+1)` = 8+2lvl | 8 |
| Gloves | 10 | 1.0 | **0.5** | 1 | `round(2.5*(t+1))+lvl*round(0.5*(t+1))` = 5+lvl | 5 |
| Rapier | 10 | 1.0 | 1.0 | 1 | `4*(t+1)+lvl*(t+1)` = 8+2lvl, +1 DR (defenseFactor) | 8 |
| Cudgel | 10 | **1.40** | 1.0 | 1 | `4*(t+1)+lvl*(t+1)` = 8+2lvl | 8 |
| MagesStaff | 10 | 1.0 | 1.0 | 1 | `round(3*(t+1))+lvl*(t+1)` = 6+2lvl | 6 |

min(lvl) for all tier 1 = `1+lvl`.

**Abilities (tier 1):**
- **WornShortsword** — *Cleave* (shared static `Sword.cleaveAbility`): hits all enemies adjacent to both attacker and primary target, dmgBoost = `3+lvl`.
- **Dagger** — *Sneak Attack*: on surprise, damage rolled from `min + 0.75*(max-min)` to `max` (75%→100% of range) instead of full min-max. *Ability* `Dagger.sneakAbility(maxDist=5, invisTurns=2+lvl)`: teleport behind target + grant Invisibility.
- **Gloves** — 2x attack speed (DLY 0.5). *Ability*: `Sai.comboStrikeAbility`, dmgBoost = `3+lvl`.
- **Rapier** — +1 DR. *Ability* `Rapier.lungeAbility` (shared with Katana): jump adjacent to target, attack with dmgBoost = `5+round(1.5*lvl)`.
- **Cudgel** — +40% ACC. *Ability* `Mace.heavyBlowAbility` (shared with HandAxe/BattleAxe/WarHammer): on surprise dmgBoost = `3+round(1.5*lvl)` and applies Daze unless target killed; otherwise dmgBoost=0 and multiplier capped at 1.
- **MagesStaff** — `unique=true`, can imbue a Wand. Battlemage subclass: on-hit triggers imbued wand at 0.5x charge cost. No duelist ability.

### Tier 2 (`WEP_T2`, probs all 2 except Pickaxe=0: Shortsword, HandAxe, Spear, Quarterstaff, Dirk, Sickle, Pickaxe)

| Weapon | STRReq(0) | ACC | DLY | RCH | max(lvl) formula | max(0) |
|---|---|---|---|---|---|---|
| Shortsword | 12 | 1.0 | 1.0 | 1 | `4*(t+1)+lvl*(t+1)` = 12+3lvl | 12 |
| HandAxe | 12 | **1.32** | 1.0 | 1 | `4*(t+1)+lvl*(t+1)` = 12+3lvl | 12 |
| Spear | 12 | 1.0 | **1.5** | **2** | `round(6.67*(t+1))+lvl*round(1.33*(t+1))` = 20+4lvl | 20 |
| Quarterstaff | 12 | 1.0 | 1.0 | 1 | `4*(t+1)+lvl*(t+1)` = 12+3lvl, +2 DR | 12 |
| Dirk | 12 | 1.0 | 1.0 | 1 | `4*(t+1)+lvl*(t+1)` = 12+3lvl | 12 |
| Sickle | 12 | **0.68** | 1.0 | 1 | `round(6.67*(t+1))+lvl*(t+1)` = 20+3lvl | 20 |
| Pickaxe | 14* | 1.0 | 1.0 | 1 | base formula (tier 2 dmg) | — |

min(lvl) for all tier 2 = `2+lvl`. *Pickaxe: STRReq uses tier+1 (i.e. tier-3 STR cost = 14) while damage uses tier 2.

**Abilities (tier 2):**
- **Shortsword** — Cleave, dmgBoost = `4+lvl`.
- **HandAxe** — +32% ACC. Heavy Blow, dmgBoost = `4+round(1.5*lvl)`.
- **Spear** — 0.67x speed (DLY 1.5), reach 2. *Ability* `Spear.spikeAbility` (shared with Glaive): attack at range 2; if target not adjacent, knocks it back along the ballistica; dmgBoost = `9+round(2*lvl)`.
- **Quarterstaff** — +2 DR. *Ability*: instant-cast `DefensiveStance` buff for `3+lvl` turns.
- **Dirk** — Sneak Attack: 67%→100% of range on surprise. `Dagger.sneakAbility(maxDist=4, invisTurns=2+lvl)`.
- **Sickle** — -32% ACC. *Ability* `Sickle.harvestAbility` (shared with WarScythe): replaces normal damage with a stacking bleed (`HarvestBleedTracker`), bleedAmt = `round(15+2.5*lvl)`.
- **Pickaxe** — quest item (`items/quest/Pickaxe.java`), `unique=true, bones=false, levelKnown=true`, survives lost-inventory on Mining level. Duelist ability deals bonus damage vs INORGANIC enemies.

### Tier 3 (`WEP_T3`, probs all 2: Sword, Mace, Scimitar, RoundShield, Sai, Whip)

| Weapon | STRReq(0) | ACC | DLY | RCH | max(lvl) formula | max(0) |
|---|---|---|---|---|---|---|
| Sword | 14 | 1.0 | 1.0 | 1 | `4*(t+1)+lvl*(t+1)` = 16+4lvl | 16 |
| Mace | 14 | **1.28** | 1.0 | 1 | `4*(t+1)+lvl*(t+1)` = 16+4lvl | 16 |
| Scimitar | 14 | 1.0 | **0.8** | 1 | `4*(t+1)+lvl*(t+1)` = 16+4lvl | 16 |
| RoundShield | 14 | 1.0 | 1.0 | 1 | `round(3*(t+1))+lvl*(t-1)` = 12+2lvl, defenseFactor=DRMax()=4+lvl | 12 |
| Sai | 14 | 1.0 | **0.5** | 1 | `round(2.5*(t+1))+lvl*round(0.5*(t+1))` = 10+2lvl | 10 |
| Whip | 14 | 1.0 | 1.0 | **3** | `5*t+lvl*t` = 15+3lvl | 15 |

min(lvl) for all tier 3 = `3+lvl`.

**Abilities (tier 3):**
- **Sword** — Cleave, dmgBoost = `5+lvl`. `CleaveTracker` buff: on kill, refunds the cleave charge for 4 turns (free re-cleave chain).
- **Mace** — +28% ACC. Heavy Blow, dmgBoost = `5+round(1.5*lvl)`, applies Daze if target not killed.
- **Scimitar** — 1.25x speed (DLY 0.8). *Ability*: `SwordDance` buff for `3+lvl` turns, grants +0.6 attack-speed multiplier while active.
- **RoundShield** — defenseFactor = DRMax() = `4+lvl`. *Ability* `guardAbility` (shared with Greatshield): `GuardTracker` buff for `5+lvl` turns, tracks `hasBlocked`.
- **Sai** — 2x speed (DLY 0.5). *Ability* `comboStrikeAbility` (shared with Gloves/Gauntlet): `ComboStrikeTracker` tracks hits within a 5-turn window; each combo level adds +multiPerHit damage multiplier and +boostPerHit flat boost; dmgBoost = `4+lvl`.
- **Whip** — reach 3. *Ability*: attacks ALL enemies in FOV the hero `canAttack`, multi=1, boost=0 (pure AoE proc, no extra damage).

### Tier 4 (`WEP_T4`, probs all 2: Longsword, BattleAxe, Flail, RunicBlade, AssassinsBlade, Crossbow, Katana)

| Weapon | STRReq(0) | ACC | DLY | RCH | max(lvl) formula | max(0) |
|---|---|---|---|---|---|---|
| Longsword | 16 | 1.0 | 1.0 | 1 | `4*(t+1)+lvl*(t+1)` = 20+5lvl | 20 |
| BattleAxe | 16 | **1.24** | 1.0 | 1 | `4*(t+1)+lvl*(t+1)` = 20+5lvl | 20 |
| Flail | 16 | **0.8** | 1.0 | 1 | `round(7*(t+1))+lvl*round(1.6*(t+1))` = 35+8lvl | 35 |
| RunicBlade | 16 | 1.0 | 1.0 | 1 | `5*t+round(lvl*(t+2))` = 20+6lvl | 20 |
| AssassinsBlade | 16 | 1.0 | 1.0 | 1 | `4*(t+1)+lvl*(t+1)` = 20+5lvl | 20 |
| Crossbow | 16 | 1.0 | 1.0 | 1 | `4*(t+1)+lvl*t` = 20+4lvl | 20 |
| Katana | 16 | 1.0 | 1.0 | 1 | `4*(t+1)+lvl*(t+1)` = 20+5lvl, +3 DR | 20 |

min(lvl) for all tier 4 = `4+lvl`.

**Abilities (tier 4):**
- **Longsword** — Cleave, dmgBoost = `6+lvl`.
- **BattleAxe** — +24% ACC. Heavy Blow, dmgBoost = `5+round(1.5*lvl)`.
- **Flail** — -20% ACC, **cannot get surprise-attack bonus**. *Ability*: Spin — builds up to 3 stacks (`SpinAbilityTracker`); each spin grants `+(8+2*lvl)` bonus damage on the next attack with `INFINITE_ACCURACY` (guaranteed hit), consumed on use.
- **RunicBlade** — max formula uses tier 3 base + tier 5 scaling. *Ability*: `RunicSlashTracker`, boost = `3+0.5*lvl` — multiplies the chance of the weapon's enchant proc on the next hit (`genericProcChanceMultiplier`); the attack itself deals normal damage (multi=1, boost=0) but massively amplifies any enchant effect.
- **AssassinsBlade** — Sneak Attack: 50%→100% of range on surprise. `Dagger.sneakAbility(maxDist=3, invisTurns=2+lvl)`.
- **Crossbow** — `dartMin(lvl)=4+lvl`, `dartMax(lvl)=12+3lvl` — boosts equipped Dart damage. *Ability*: `ChargedShot` buff — next dart shot gets `INFINITE_ACCURACY`; on hit triggers an Elastic-style knockback (`WandOfBlastWave.throwChar`, strength 4) and AoE proc to all chars within 3 tiles (`Dart.processChargedShot`).
- **Katana** — +3 DR. *Ability* `Rapier.lungeAbility`, dmgBoost = `8+round(2*lvl)`.

### Tier 5 (`WEP_T5`, probs all 2: Greatsword, WarHammer, Glaive, Greataxe, Greatshield, Gauntlet, WarScythe)

| Weapon | STRReq(0) | ACC | DLY | RCH | max(lvl) formula | max(0) |
|---|---|---|---|---|---|---|
| Greatsword | 18 | 1.0 | 1.0 | 1 | `4*(t+1)+lvl*(t+1)` = 24+6lvl | 24 |
| WarHammer | 18 | **1.20** | 1.0 | 1 | `4*(t+1)+lvl*(t+1)` = 24+6lvl | 24 |
| Glaive | 18 | 1.0 | **1.5** | **2** | `round(6.67*(t+1))+lvl*round(1.33*(t+1))` = 40+8lvl | 40 |
| Greataxe | **20*** | 1.0 | 1.0 | 1 | `5*(t+4)+lvl*(t+1)` = 45+6lvl | 45 |
| Greatshield | 18 | 1.0 | 1.0 | 1 | `round(3*(t+1))+lvl*(t-1)` = 18+3lvl, defenseFactor=DRMax()=6+2lvl | 18 |
| Gauntlet | 18 | 1.0 | **0.5** | 1 | `round(2.5*(t+1))+lvl*round(0.5*(t+1))` = 15+3lvl | 15 |
| WarScythe | 18 | **0.8** | 1.0 | 1 | `round(6.67*(t+1))+lvl*(t+1)` = 40+6lvl | 40 |

min(lvl) for all tier 5 = `5+lvl`. *Greataxe STRReq computed using tier+1 (=6) → base 20 STR instead of 18.

**Abilities (tier 5):**
- **Greatsword** — Cleave, dmgBoost = `7+lvl`.
- **WarHammer** — +20% ACC. Heavy Blow, dmgBoost = `6+round(1.5*lvl)`.
- **Glaive** — 0.67x speed (DLY 1.5), reach 2. `Spear.spikeAbility`, dmgBoost = `12+round(2.5*lvl)`.
- **Greataxe** — *Ability* requires HP < 50%: attack with dmgBoost = `15+2*lvl` and `INFINITE_ACCURACY`; on kill, grants `hero.next()` (free extra turn).
- **Greatshield** — defenseFactor = DRMax() = `6+2lvl`. `guardAbility` (RoundShield's), duration = `3+lvl`.
- **Gauntlet** — 2x speed (DLY 0.5). `comboStrikeAbility` (Sai's), dmgBoost = `5+lvl`.
- **WarScythe** — -20% ACC. `harvestAbility` (Sickle's), bleedAmt = `round(30+4.5*lvl)`.

> Note: current source has no Sickle-vs-undead or WarScythe-sweep mechanic; both share the generic `harvestAbility` bleed-replacement ability described above.

---

## 3. Missile Weapon Base Formulas (`MissileWeapon.java`)

- `min(lvl) = 2*tier + lvl`
- `max(lvl) = 5*tier + tier*lvl`  (per-weapon overrides below)
- `STRReq(lvl) = MeleeWeapon.STRReq(tier, lvl) - 1` (missiles are 1 STR easier than melee of same tier; minus mastery bonus if applicable)
- **adjacentAccFactor**: if attacker adjacent to target → x0.5 ACC (hero: `0.5 + 0.25*PointBlankTalent`); if not adjacent (ranged) → x1.5 ACC bonus.
- `defaultQuantity() = 3` for most missiles.
- `durabilityPerUse(lvl) = (MAX_DURABILITY / baseUses) * 1.5^lvl`, modified by talents/Holster/Augment/Ring of Sharpshooting. `MAX_DURABILITY = 100`.
- `value() = 5 * tier * quantity`, modified by enchant/curse/level.

### Tier 1 (`MIS_T1`, probs `{3,3,3,0}`: ThrowingStone, ThrowingKnife, ThrowingSpike, Dart[never drops])

| Weapon | tier | baseUses | min(lvl) | max(lvl) | Notes |
|---|---|---|---|---|---|
| ThrowingStone | 1 | 5 | 2+lvl | 5+lvl | `bones=false`; `value()` halved |
| ThrowingKnife | 1 | 5 | 2+lvl | `6*1 + 2*lvl` = 6+2lvl | Sneak: 75%→100% of range on surprise |
| ThrowingSpike | 1 | 12 | 2+lvl | 5+lvl | no overrides (pure base formula) |

### Tier 2 (`MIS_T2`, probs all 3: FishingSpear, ThrowingClub, Shuriken)

| Weapon | tier | baseUses | min(lvl) | max(lvl) | Notes |
|---|---|---|---|---|---|
| FishingSpear | 2 | default | 4+lvl | 10+2lvl | proc: vs Piranha, `damage = max(damage, defender.HP/2)` (guaranteed massive dmg) |
| ThrowingClub | 2 | 12 | 4+lvl | `4*2 + 2*lvl` = 8+2lvl | `sticky=false`, `pickupDelay()=0` (instant pickup) |
| Shuriken | 2 | 5 | 4+lvl | `4*2 + 2*lvl` = 8+2lvl | On throw, grants `ShurikenInstantTracker` (20 turns); while active, next throw has `castDelay=0` (instant second throw) |

### Tier 3 (`MIS_T3`, probs all 3: ThrowingSpear, Kunai, Bolas)

| Weapon | tier | baseUses | min(lvl) | max(lvl) | Notes |
|---|---|---|---|---|---|
| ThrowingSpear | 3 | default | 6+lvl | 15+3lvl | no overrides |
| Kunai | 3 | 8 | 6+lvl | `4*3 + 3*lvl` = 12+3lvl | Sneak: 60%→100% of range on surprise |
| Bolas | 3 | 5 | `2*(3-1)` = 4 (flat, no lvl scaling) | `3*3 + (3-1)*lvl` = 9+2lvl | proc: applies `Cripple.DURATION/2` (rooting effect) |

### Tier 4 (`MIS_T4`, probs all 3: Javelin, Tomahawk, HeavyBoomerang)

| Weapon | tier | baseUses | min(lvl) | max(lvl) | Notes |
|---|---|---|---|---|---|
| Javelin | 4 | default | 8+lvl | 20+4lvl | no overrides |
| Tomahawk | 4 | 5 | `round(1.5*4)+lvl` = 6+lvl | `round(4*4)+(4-1)*lvl` = 16+3lvl | proc: applies Bleeding, amount = `augment.damageFactor(Random.NormalFloat(minBleed, maxBleed))`, `minBleed(lvl)=3+lvl/2`, `maxBleed(lvl)=6+lvl` |
| HeavyBoomerang | 4 | 5 | 8+lvl | `4*4 + (4-1)*lvl` = 16+3lvl | `sticky=false`. On hit or miss, spawns `CircleBack` buff (5-turn delay) that returns the boomerang to the hero's cell and re-attacks original target (or new occupant) — second hit. `adjacentAccFactor=1.5` always on the return throw (treated as ranged) |

### Tier 5 (`MIS_T5`, probs all 3: Trident, ThrowingHammer, ForceCube)

| Weapon | tier | baseUses | min(lvl) | max(lvl) | Notes |
|---|---|---|---|---|---|
| Trident | 5 | default | 10+lvl | 25+5lvl | no overrides |
| ThrowingHammer | 5 | 12 | 10+lvl | `4*5 + 5*lvl` = 20+5lvl | `sticky=false`, `pickupDelay()=0` |
| ForceCube | 5 | 5 | 10+lvl | 25+5lvl (base) | `sticky=false`, no hit sound. `onThrow`: if target cell is a pit with no char, behaves normally; else hits primary target + presses all 8 neighboring cells (triggers traps except Tengu Dart Trap), hits all chars in the 3x3 area (furthest-to-closest for elastic-style resolution), then `WandOfBlastWave.BlastWave.blast(cell)` — full knockback AoE. With Sniper subclass: applies `SnipersMark` to primary target. |

---

## 4. Darts (`weapon/missiles/darts/`)

### Dart.java (base)
- `tier=1`, `levelKnown=true`, `baseUses=1000` (effectively unlimited), `setID=0` (all dart variants share one inventory stack/slot), `defaultQuantity=2`, `value()` halved, `isUpgradable=false`.
- `min(lvl) = 1+lvl` (or `bow.dartMin(lvl)` if Crossbow equipped)
- `max(lvl) = 2+2lvl` (or `bow.dartMax(lvl)` if Crossbow equipped)
- With Crossbow `ChargedShot` active: +`(4 + bow.lvl)` bonus to both min and max.

### TippedDart (abstract base, 12 subclasses)
- `tier=2` but **same damage as regular Dart** (tier-1 damage formula). `baseUses=1`. Consumes 1 use; remaining stack reverts to plain `Dart`. `value() = 7.5 * quantity`. `DURABLE_TIPS` talent divides usage cost.

| Dart | Seed source | Effect |
|---|---|---|
| AdrenalineDart | Sungrass? *(actually Swiftthistle)* | If same alignment: `Adrenaline.DURATION` Adrenaline buff on target. If hostile: `Cripple.DURATION/2`. Skipped on hero during charged shot. |
| BlindingDart | Blindweed | `Blindness.DURATION` Blindness — only on enemies during charged shot, or always if alignments differ |
| ChillingDart | Icecap | `Chill.DURATION` if target is in water, else 6 turns of Chill |
| CleansingDart | Mageroyal | Same alignment: `PotionOfCleansing.cleanse(defender, Cleanse.DURATION*2)`. Hostile: strips most buffs (excluding ChampionEnemy-type); on a hunting/fleeing Mob, delays the state reset to WANDERING by 1 turn (via FlavourBuff) so the dart damage doesn't immediately re-trigger aggro. |
| HealingDart | Sungrass | `PotionOfHealing.cure(defender)` + `Healing` buff healing `0.5*defender.HT + 30` over time (heal-over-time, 0.25 rate) |
| HolyDart | Starflower | If same alignment: `Bless.DURATION` Bless. If target is UNDEAD/DEMONIC: deals bonus damage `Random.NormalIntRange(10+depth/3, 20+depth/3)` with `HolyDamage`. Else (hostile, non-unholy, not charged shot): also applies Bless. |
| IncendiaryDart | Firebloom | `Burning.reignite(defender)` — only on enemies during charged shot, or always if alignments differ |
| ParalyticDart | Earthroot | `Paralysis` for 5 turns — only enemies during charged shot |
| PoisonDart | Sorrowmoss | `Poison.set(3 + depth/2)` — only enemies during charged shot |
| RotDart | Rotberry | If BOSS/MINIBOSS: `Corrosion.set(5, depth/3)`; else `Corrosion.set(10, depth)`. Charged shot: skipped if same alignment. `durabilityPerUse = MAX_DURABILITY/5` (always 5 uses) |
| ShockingDart | Stormvine | Direct damage `Random.NormalIntRange(5+depth/4, 10+depth/4)` via Electricity — only enemies during charged shot, or always if alignments differ |
| DisplacingDart | Fadeleaf | Teleports enemy to a cell 8-10 tiles from the hero (prefers visible cells closest to defender's current position; grants vision if it lands in fog). Only affects enemies during charged shot; `IMMOVABLE` targets unaffected. |

(Seed→Dart mapping per project memory: Rotberry→Rot, Sungrass→Healing, Fadeleaf→Displacing, Icecap→Chilling, Firebloom→Incendiary, Sorrowmoss→Poison, Swiftthistle→Adrenaline, Blindweed→Blinding, Stormvine→Shocking, Earthroot→Paralytic, Mageroyal→Cleansing, Starflower→Holy.)

---

## 5. Bombs (`items/bombs/`)

### Bomb.java (base)
- `value() = 15 * quantity`. `isUpgradable=false`, `isIdentified=true`.
- `explosionRange() = 1` (3x3 area) by default.
- Base damage to each affected char: `Random.NormalIntRange(4 + scalingDepth, 12 + 3*scalingDepth) - drRoll()`.
- `explodesDestructively()=true` by default: destroys flammable terrain, triggers/destroys item heaps and other bombs in range, damages all chars in range.
- Throwing with "Light & Throw" ignites a `Fuse` (2-turn delayed `Actor`) that explodes the bomb when it ticks down, unless snuffed (picked up / frozen).
- `Item.random()`: 1-in-4 chance to become a `DoubleBomb` (stacks of 2, picked up as "1+1 free").
- **EnhanceBomb recipe** — combine a Bomb + ingredient to craft a special bomb (costs listed):

| Ingredient | Result bomb | Cost |
|---|---|---|
| PotionOfFrost | FrostBomb | 0 |
| ScrollOfMirrorImage | WoollyBomb | 0 |
| PotionOfLiquidFlame | Firebomb | 1 |
| ScrollOfRage | Noisemaker | 1 |
| PotionOfInvisibility | SmokeBomb | 2 |
| ScrollOfRecharging | FlashBangBomb | 2 |
| PotionOfHealing | RegrowthBomb | 3 |
| ScrollOfRemoveCurse | HolyBomb | 3 |
| GooBlob (quest item) | ArcaneBomb | 6 |
| MetalShard (quest item) | ShrapnelBomb | 6 |

### Bomb subtypes

| Bomb | explosionRange | explodesDestructively | value | Unique effect |
|---|---|---|---|---|
| Firebomb | 2 | yes | `qty*(20+30)` | Seeds `Fire` blob (volume 10, or 2 if cell is a pit) in every cell within range 2 |
| FlashBangBomb | 2 | yes | `qty*(20+30)` | All chars in range take `round(baseDmg/4)` Electricity damage (25% of normal bomb damage) and get `Paralysis.DURATION` Paralysis; draws lightning arcs from blast center to each target |
| FrostBomb | 2 | yes | `qty*(20+30)` | Seeds `Freezing` blob (volume 10) in range; each char in range gets `Frost` buff for 2 turns |
| HolyBomb | 2 | yes | `qty*(20+30)` | Standard blast, plus: UNDEAD/DEMONIC chars take extra `round(0.5 * Random.NormalIntRange(depth+4, 12+3*depth))` HolyDamage |
| Noisemaker | 2 | yes | `qty*(20+40)` | Two-stage fuse: first trigger arms it (cannot be snuffed after); each subsequent turn, if a char is on its cell it explodes immediately, else ticks an alert counter (resets to 6) that screams + `beckon`s all mobs on the level toward it, then resets |
| RegrowthBomb | 3 | **no** (non-destructive) | `qty*(20+30)` | Allied chars in range get cured + healed (like Potion of Healing). Seeds `Regrowth` blob (volume 10) everywhere in range. On valid grass/empty tiles, plants `Random.chances({0,0,2,1})` random seeds (weighted toward tier 3 seeds) plus one extra special plant chosen via `Random.chances({0,6,3,1})`: Dewcatcher (wt 6), Seedpod (wt 3), or Starflower (wt 1) |
| ShrapnelBomb | 8 | **no** (non-destructive) | `qty*(20+50)` | Uses shadow-casting FOV (range 8) instead of a fixed blast radius; every char with line-of-sight to the blast takes standard bomb damage (`Random.NormalIntRange(4+depth, 12+3*depth) - drRoll()`) |
| SmokeBomb | 2 | yes | `qty*(20+40)` | Seeds `SmokeScreen` blob (volume 40 per cell) across the blast area; any leftover volume (1000 total budget minus 40*cells) dumps onto the center cell |
| WoollyBomb | 2 (search radius +2 = 4) | yes | `qty*(20+30)` | Spawns a `Sheep` NPC (HP 20 on boss levels, else 200) on every empty, non-pit cell within range+2 of the blast |
| ArcaneBomb | 2 | **no** (non-destructive) | `qty*(20+30)` | All chars in range take `Random.NormalIntRange(4+depth, 12+3*depth)` damage that **pierces armor** (no `drRoll()` subtraction); fuse emits Goo-particle "warning" VFX while burning |

---

## 6. Weapon Enchantments (`items/weapon/enchantments/`)

`level = max(0, weapon.buffedLvl())`. `procChanceMultiplier(attacker)` is a talent/buff-based multiplier (usually 1). `powerMulti = max(1, procChance)` scales most effect magnitudes.

| Enchant | Proc chance (lvl 0/1/2) | Effect |
|---|---|---|
| **Blazing** | 33% / 50% / 60% — `(lvl+1)/(lvl+3)` | Ignites target with `Burning` (8s) if not already burning; if already burning, deals direct fire damage instead |
| **Blocking** | 10% / ~12% / ~14% — `(lvl+4)/(lvl+40)` | Grants attacker a `BlockBuff` shield of `round(powerMulti*(2+lvl))` |
| **Blooming** | 33% / 50% / 60% — `(lvl+1)/(lvl+3)` | Spawns `(1+0.1*lvl)*powerMulti` plants (rounded probabilistically) near target |
| **Chilling** | 25% / 40% / 50% — `(lvl+1)/(lvl+4)` | Adds `3*powerMulti` turns of `Chill`, capped at `6*powerMulti` total |
| **Corrupting** | ~20% / ~23% / ~26% — `(lvl+5)/(lvl+25)` | If the hit would be lethal (`damage >= defender.HP`) and target is a non-immune, alive Mob with no existing Corruption: converts it to an ally (`Corruption` buff) instead of killing it |
| **Elastic** | 20% / 33% / 43% — `(lvl+1)/(lvl+5)` | Knocks the target back along the ballistica past them, via `WandOfBlastWave.throwChar` with strength `round(2*powerMulti)` |
| **Grim** | up to 50%+5%/lvl, scaled by target's missing-HP% | Attaches `GrimTracker` (maxChance) which can convert the killing blow into an instant-kill proc, deferred via `Char.damage` so true final damage is known |
| **Kinetic** | always (passive) | Adds any `ConservedDamage` accumulated from a previous dodge/block onto this hit; tracks final damage via `KineticTracker` for future conservation |
| **Lucky** | 10% / ~12% / ~14% — `(lvl+4)/(lvl+40)` | Applies `LuckProc` to target with `ringLevel = -10 + round(5*powerMulti)` — i.e. triggers a Ring of Wealth-style "luck" roll (better loot/curse-cleanse on death) |
| **Projecting** | n/a (passive, no on-hit proc) | Increases weapon reach by 1 (affects `reachFactor` and missile throw range) |
| **Shocking** | flat 33% — `1/3` | Arcs Electricity damage to up to nearby enemies within range 2 (excludes the primary defender) |
| **Unstable** | always | Re-rolls and applies a random enchantment from `[Blazing, Chilling, Kinetic, Shocking, Blocking, Blooming, Elastic, Lucky, Projecting, Corrupting, Grim, Vampiric]` (delegates `proc()` to a random other enchant each hit) |
| **Vampiric** | `0.05 + 0.25*missingHPpercent` (attacker's missing HP) | Heals attacker for `round(damage * 0.5 * powerMulti)`; only triggers vs hostile/non-neutral (or Mimic) targets |

---

## 7. Weapon Curses (`items/weapon/curses/`)

All curse procs are checked alongside normal enchant procs (cursed weapons replace the enchant slot).

| Curse | Proc chance | Effect |
|---|---|---|
| **Annoying** | 1/20 (5%) | Beckons (alerts/summons) every mob on the level toward the attacker |
| **Displacing** | 1/12 (~8.3%) | Teleports the defender to a random location (`ScrollOfTeleportation.teleportChar`), unless `IMMOVABLE` |
| **Dazzling** | 1/10 (10%) | Blinds every char with the target in FOV — full `Blindness.DURATION` for the attacker, half-duration for everyone else |
| **Explosive** | (passive durability hook) | When equipped on ammo via a parent enchant, copies the `durability` from the parent MissileWeapon's Explosive enchant (links missile durability to the explosive effect) |
| **Sacrificial** | 1/10 (10%) | Bleeds the attacker for `(missingHP%)^2 * HT / 8`, scaled by a random roll — costs the wielder HP to "power" the hit |
| **Wayward** | 1/4 (25%) | Toggle: if `WaywardBuff` already active on attacker, removes it; else (25% chance) applies `WaywardBuff` for its duration — causes the weapon to occasionally attack a random nearby target instead of the intended one |
| **Polarized** | 1/2 (50%) | 50% chance to deal `1.5x` damage, 50% chance to deal **0** damage — high variance |
| **Friendly** | 1/10 (10%) | If the attacker is Charmed and currently charmed-toward the defender, zeroes the damage entirely (10% chance, on top of the charm check, to otherwise misfire) |
