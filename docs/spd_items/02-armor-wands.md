# SPD Spec: Armor & Wands

Source: `core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/{armor,wands}/`

---

## 1. Armor

### 1.1 Base mechanics (`Armor.java`)

**Tiers and DR formula**

`DRMax(lvl)`:
- If challenge `NO_ARMOR` active: `1 + tier + lvl + augment.defenseFactor(lvl)`
- Else: `max = tier*(2+lvl) + augment.defenseFactor(lvl)`; if `lvl > max` then `((lvl-max)+1)/2` else `max`

`DRMin(lvl)`:
- If `NO_ARMOR`: `0`
- Else if `lvl >= DRMax(lvl)`: `lvl - DRMax(lvl)`
- Else: `lvl`

So DR range = `[DRMin(lvl), DRMax(lvl)]`, randomized per hit (`Random.NormalIntRange`).

**STR requirement**

```
STRReq(tier, lvl) = (8 + round(tier*2)) - floor((sqrt(8*lvl+1)-1)/2)
```
- `lvl` clamped to `>= 0` for this formula (negative levels don't reduce further).
- Mastery potion (`PotionOfMastery`) subtracts an extra 2.
- Diminishing returns: each point of `lvl` reduces STRReq by 1 up to lvl 0, then increasingly slower (the `sqrt` term) — net effect is STRReq drops by 1 at level +1, +3, +6, +10, etc.

**Augments**

| Augment | evaFactor | defFactor |
|---|---|---|
| EVASION | +2 | -1 |
| DEFENSE | -2 | +1 |
| NONE | 0 | 0 |

- `evasionFactor(level) = round((2+level) * evaFactor)`
- `defenseFactor(level) = round((2+level) * defFactor)`

**Evasion factor** (`Armor.evasionFactor`):
- Returns `0` if armor has `Glyph.Stone` (unless `Stone.testingEvasion()`).
- Else: base evasion `/= 1.5^(STRReq - STR)` if hero is STR-encumbered (STR < STRReq).
- Plus Momentum talent bonus.
- Plus `augment.evasionFactor(buffedLvl)`.

**Speed factor** (`Armor.speedFactor`):
- `/= 1.2^(STRReq - STR)` if encumbered.

**Value**

```
value() = 20 * tier
        * 1.5 if hasGoodGlyph
        / 2   if cursedKnown && (cursed || hasCurseGlyph)
        * (level()+1) if levelKnown && level() > 0
        min 1
```

**Random generation** (`Armor.random()`):
- Level distribution: +0 → 75%, +1 → 20%, +2 → 5%.
- 30% × `ParchmentScrap.curseChanceMultiplier()` chance: cursed + inscribed with a random curse glyph (`Glyph.randomCurse()`).
- Else 15% × `ParchmentScrap.enchantChanceMultiplier()` chance: inscribed with a random "good" glyph (weighted by `typeChances`).

### 1.2 Generic armor tiers

| Class | Tier | STR @ +0 | DR range @+0 | Value @+0 | Notes |
|---|---|---|---|---|---|
| ClothArmor | 1 | 10 | 0–2 | 20 | `bones=false` |
| LeatherArmor | 2 | 12 | 0–4 | 40 | |
| MailArmor | 3 | 14 | 0–6 | 60 | |
| ScaleArmor | 4 | 16 | 0–8 | 80 | |
| PlateArmor | 5 | 18 | 0–10 | 100 | |

(DR range @+0 = `[0, tier*2]` since `lvl=0` and `DRMax(0)=tier*2`.)

### 1.3 Glyphs (`items/armor/glyphs/`)

`Glyph.typeChances = {50, 40, 10}` → common (50%) / uncommon (40%) / rare (10%), drawn from arrays of 4/6/3 glyphs respectively when an armor rolls a "good" glyph.

All glyphs use `procChanceMultiplier(defender)` (wearer-side) or `genericProcChanceMultiplier(owner)` scaling — both are talent/curse-aware multipliers on proc strength/chance.

| Glyph | Tier | Color | Effect |
|---|---|---|---|
| **Affection** | common | Pink `#FF4488` | On hit taken: chance `(lvl+3)/(lvl+20)` to Charm the attacker (duration scaled by chance overflow). |
| **Camouflage** | common | Green `#448822` | While in high grass, grants Invisibility for `3 + lvl/2` turns (scaled) when trampling grass. |
| **Flow** | common | Blue `#0000FF` | While standing in water, speed multiplier `(2 + 0.5*lvl)` (scaled); emits blue light particles. |
| **Obfuscation** | common | Grey `#888888` | Stealth boost `(1 + lvl/3)` (scaled); reduces chance of being noticed by enemies. |
| **Potential** | uncommon | White (glow 0.6) | On hit taken: chance `(lvl+1)/(lvl+6)` (Hero only) recharges a random wand by `powerMulti` charge fraction. |
| **Repulsion** | uncommon | White | On hit taken (adjacent only): chance `(lvl+1)/(lvl+5)` to knock the attacker back 2 cells (BlastWave-style throw). |
| **Swiftness** | uncommon | Yellow `#FFFF00` | If no enemy within 3-tile passable path, speed multiplier `(1.2 + 0.04*lvl)` (scaled); yellow light particles. |
| **Thorns** | uncommon | Red `#660022` | On hit taken from a different-alignment attacker: chance `(lvl+2)/(lvl+12)` to apply Bleeding for `4+lvl` turns (scaled). |
| **Entanglement** | rare | Brown `#663300` | On hit taken: 25% chance (scaled) to root attacker via Earthroot.Armor buff at level `5+2*lvl` (scaled). |
| **AntiMagic** | rare | Teal `#88EEFF` | Passive: resists a large set of magic damage sources (wands, holy spells, traps, bombs, certain mob attacks) listed in `RESISTS`; reduces incoming magic damage via `drRoll(owner, level)` = `NormalIntRange(round(lvl*mult), round((3+1.5*lvl)*mult))`. |
| **Stone** | rare | Dark grey `#222222` | Sets evasion factor to 0 (wearer can't dodge via evasion bonus); on hit taken, recomputes a "true" hit-chance from accuracy/evasion and applies 75% of the dodge-chance as flat damage reduction (clamped `[0.25,1]` multiplier). |
| **Brimstone** | rare (special) | Orange `#FF4400` | No active proc; grants immunity to Fire/Burning (checked in `Char.isImmune`). |
| **Viscosity** | (common-tier, listed separately) | Purple `#8844CC` | On hit taken: defers a fraction `(lvl+1)/(lvl+6)` (scaled) of damage into a `DeferedDamage` buff that ticks 10%/turn instead of all at once. |

*(Brimstone and Viscosity placement in common/uncommon/rare arrays not fully enumerated from source excerpt above; treat as "good glyph pool" members per `typeChances`.)*

### 1.4 Curses (`items/armor/curses/`)

All 8 are selected via `Glyph.randomCurse()`. Proc chance uses `procChanceMultiplier(defender)`.

| Curse | Proc chance (base) | Effect |
|---|---|---|
| **AntiEntropy** | 1/8 | Freezes the 8 neighbouring cells around defender (`Freezing.affect`). |
| **Bulk** | passive (speed) | While standing on a door tile, multiplies speed (slows movement); emits shadow particles. No direct proc effect — hooks `Char.speed()`. |
| **Corrosion** | 1/10 | Splashes black ooze on all 9 cells around defender (self + neighbours), likely applying Ooze/ corroding nearby items. |
| **Displacement** | 1/20 | Teleports the defender (wearer) randomly; returns `0` damage when it procs (cancels the hit). |
| **Metabolism** | 1/6 (Hero only) | Heals hero a small amount (≈1 HP per 10 Hunger.STARVING/100 ticks-worth) while increasing hunger. |
| **Multiplicity** | 1/20 | Spawns a duplicate at a free neighbouring cell — 50% chance a `MirrorImage` of the Hero (if defender is Hero), else duplicates the attacker. |
| **Overgrowth** | 1/20 | Plants a random seed-derived plant at defender's position (couches it immediately). |
| **Stench** | 1/8 | Seeds a 250-strength `ToxicGas` blob at defender's position. |

---

## 2. Class Armor (`ClassArmor.java` + subclasses)

All class armors: `tier=5`, `levelKnown=true`, `cursedKnown=true`, `defaultAction=AC_ABILITY`, `bones=false`, `value()=0`.

**Charge mechanic**: `charge` field 0–100. `Charger` buff (active while regen on, e.g. not resting-disabled) gains `(100/500) * RingOfEnergy.armorChargeMultiplier(target)` per tick, capped at 100. I.e. full charge in 500 turns at base rate.

**AC_TRANSFER**: special action that copies level/tier/augment/glyph/seal/curse status from a donor `Armor` item onto the ClassArmor (donor item destroyed). `ClassArmor.upgrade(owner, armor)` is the static factory: instantiates the correct subclass for `owner.heroClass`, copies properties from the donor armor, and sets `charge = 50`.

| Class | Armor name | Subclass |
|---|---|---|
| Warrior | hero's platemail | `WarriorArmor` |
| Mage | hero's robe | `MageArmor` |
| Rogue | hero's garb | `RogueArmor` |
| Huntress | hero's cloak | `HuntressArmor` |
| Duelist | hero's breastplate | `DuelistArmor` |
| Cleric | hero's vestments | `ClericArmor` |

### Armor abilities (`actors/hero/abilities/<class>/`)

Each hero picks one of several class-specific abilities (via `WndChooseAbility`), triggered from the class armor at `AC_ABILITY`, consuming `charge` (gated by `baseChargeUse`, modified by talents).

| Class | Ability | baseChargeUse |
|---|---|---|
| Warrior | Endure | — |
| Warrior | Heroic Leap | — |
| Warrior | Shockwave | 35 |
| Mage | Elemental Blast | — |
| Mage | Warp Beacon | 35 |
| Mage | Wild Magic | 25 |
| Rogue | Death Mark | 25 |
| Rogue | Shadow Clone | — |
| Rogue | Smoke Bomb | — |
| Huntress | Nature's Power | 35 |
| Huntress | Spectral Blades | 25 |
| Huntress | Spirit Hawk | — |
| Duelist | Challenge | 35 |
| Duelist | Elemental Strike | — |
| Duelist | Feint | — |
| Cleric | Ascended Form | 50 |
| Cleric | Power of Many | — |
| Cleric | Trinity | — |

(`—` = baseChargeUse not captured from a brief scan; likely defined per-class similarly to the listed values, commonly 25/35/50.)

---

## 3. Wands

### 3.1 Base mechanics (`Wand.java`)

**Charges**
- `maxCharges = initialCharges()` (base wand starts with some small max, typically 1, scales with level via `updateLevel`: `maxCharges = min(initialCharges() + level(), 10)`).
- `curCharges` starts at `maxCharges`.
- `chargesPerCast()` — default 1 (overridden per-wand, e.g. WandOfRegrowth scales 1–3).

**Recharge** (Charger buff, `partialCharge` accumulator):
- Each turn, if `curCharges < maxCharges` (and target not `MagicImmune`), `recharge()` is called.
- Base recharge rate: 1 charge every ~`10` turns at full efficiency (`turnsToCharge` derived from `Recharging`/`RingOfEnergy` and ring of wealth/energy multipliers), scaled up the more charges are missing (longer wait when near-full, faster relatively when empty — exact formula adds delay proportional to missing charges).
- `ScrollOfRecharging` instantly fills.

**Level scaling**
- `level()`: base enchant level, +1 from `curseInfusionBonus` if not cursed.
- `buffedLvl()`: level adjusted by `WandEmpower`/other buffs.
- `updateLevel()`: recomputes `maxCharges`.

**Cursed wands**
- 30% chance on generation to be `cursed = true`.
- Cursed wand zap (`collisionProperties = MAGIC_BOLT` when cursed) routes through `CursedWand.cursedZap`, which picks a random effect from 4 tiers by `EFFECT_CAT_CHANCES = {60, 30, 9, 1}` (common/uncommon/rare/very-rare):
  - **Common** (60%): BurnAndFreeze, SpawnRegrowth, RandomTeleport, RandomGas (Confusion/Toxic/Paralytic), RandomAreaEffect (Burning/Chilling/Shocking trap), Bubbles, RandomWand (zaps a random wand at scaled level), SelfOoze.
  - **Uncommon** (30%): RandomPlant (seeds a random plant), HealthTransfer (drains `2*scalingDepth` HP, half to caster as healing), Explosion (conjured bomb), LightningBolt (chain lightning + AoE shock/stun + recharges hero wands), Geyser, SummonSheep (flock trap), Levitate, Alarm (alerts all mobs / or challenge arena).
  - **Rare** (9%): SheepPolymorph (turns non-boss enemy into Sheep), CurseEquipment (hexes target or curses hero gear via CursingTrap), InterFloorTeleport, SummonMonsters (summoning trap / mirror images), FireBall (3-radius burning AoE + blast wave), ConeOfColors (90° cone, random elemental effect per target), MassInvuln (all chars invulnerable+blessed 10s), Petrify (TimeStasis on hero 100 turns).
  - **Very Rare** (1%): ForestFire (regrowth everywhere + scattered fire), SpawnGoldenMimic, AbortRetryFail (joke "crash" dialog), RandomTransmogrify (replaces item with random equipment), HeroShapeShift (HeroDisguise), SuperNova, SinkHole (delayed pitfall trap across level), GravityChaos.
  - `WondrousResin.positiveCurseEffectChance()` can force "positiveOnly" mode (hero-only), which biases effects to be beneficial/non-harmful.

**`wandProc(target, origin.buffedLvl(), chargesUsed)`**: shared static method triggering talent-driven secondary effects (Arcane Vision, Warlock SoulMark, Priest GuidingLight, Searing Light, Sunray) when a wand hits a target.

**Melee staff procs** (`onHit(MagesStaff, attacker, defender, damage)`): each wand can define bonus melee effects when used as the head of a Mage's Staff.

**`procChanceMultiplier(attacker)`**: talent/equipment-driven multiplier on proc chance/strength (e.g. Wand Preservation, Warlock talents).

### 3.2 `DamageWand` (abstract base for direct-damage wands)

- `min()/max()` → `min(buffedLvl())/max(buffedLvl())`, abstract per-wand.
- `damageRoll(lvl) = Hero.heroDamageIntRange(min(lvl), max(lvl))`, plus `WandEmpower.dmgBoost` if active (consumes 1 charge of empower buff, plays HIT_STRONG sound).
- `statsDesc()` shows `min()-max()` damage range.

### 3.3 Wand catalog (`Generator.WAND.classes`, all weight 3)

| # | Wand | Type | Charge cost | Collision props |
|---|---|---|---|---|
| 1 | WandOfMagicMissile | DamageWand | 1 | PROJECTILE |
| 2 | WandOfLightning | DamageWand (chain) | 1 | PROJECTILE |
| 3 | WandOfDisintegration | DamageWand | 1 | PROJECTILE |
| 4 | WandOfFireblast | DamageWand (cone) | 1 | — |
| 5 | WandOfCorrosion | Wand (debuff) | 1 | PROJECTILE |
| 6 | WandOfBlastWave | Wand (knockback) | 1 | — |
| 7 | WandOfLivingEarth | Wand (summon) | 1 | — |
| 8 | WandOfFrost | DamageWand (AoE freeze) | 1 | PROJECTILE |
| 9 | WandOfPrismaticLight | Wand (random elemental) | 1 | — |
| 10 | WandOfWarding | Wand (summon ward) | 1 | — |
| 11 | WandOfTransfusion | DamageWand (heal/charm/harm) | 1 | PROJECTILE |
| 12 | WandOfCorruption | Wand (mind control) | 1 | — |
| 13 | WandOfRegrowth | Wand (terrain/vegetation) | 1–3 | WONT_STOP (cone) |

### 3.4 Per-wand formulas

#### WandOfMagicMissile
- `min(lvl) = 1 + lvl`, `max(lvl) = 3 + 2*lvl` (typical MM scaling).
- Single-target projectile damage.

#### WandOfLightning
- Chain lightning: bolt arcs between nearby targets via a recursive arc algorithm; each arc applies `wandProc` and electric damage.
- Damage scales with level; total damage spread across all chained targets.

#### WandOfDisintegration
- High base damage scaling per level; AntiMagic resists.
- `DisintegrationTrap`-style: ignores armor (raw HP damage) at higher levels.

#### WandOfFireblast
- `ConeAOE` (`Ballistica` cone), burns all targets in cone with `Burning` + fire damage; ignites flammable terrain.

#### WandOfCorrosion
- Non-damage debuff wand: applies `Corrosion` buff (item-degrading) to target; `Wand` base (not `DamageWand`).

#### WandOfBlastWave
- Knockback wand: `BlastWave.blast(pos, radius)` and `throwChar(...)` push characters away from impact, dealing fall/collision damage.
- Used by armor glyph **Repulsion** for knockback.

#### WandOfLivingEarth
- Summons an `EarthGuardian` ally (golem) that fights for the hero; guardian HP/duration scale with wand level.

#### WandOfFrost
- AoE freeze: applies `Frost` buff (immobilize) + cold damage in a radius around impact.

#### WandOfPrismaticLight
- Fires multiple beams in random directions, each applying a randomly-chosen elemental effect (fire/frost/shock/etc.) to whatever it hits.

#### WandOfWarding (`Ward` NPC system)
- Summons/upgrades a `Ward` NPC (`NPC` subclass, `alignment=ALLY`, `IMMOVABLE`/`STATIC`-like).
- `Ward.tier` 1–6, each tier increases `HT`:
  - Tier 1: `HT=35`, `HP = 15 + (5-totalZaps)*4`
  - Tier 2: `HT=54`
  - Tier 3: `HT=84`
  - (tiers 4–6 continue scaling; tier ≥3 unlocks `WardSentry` behavior)
- Casting again on an existing ward increases its `tier` (up to 6) and updates its sprite (`updateTier`).
- `currentWardEnergy` accumulates `tier` values of all active wards (including Stasis ally ward) — caps total ward power.
- Wards burst `MagicMissile.WardParticle` particles proportional to `tier` on attack.

#### WandOfTransfusion
- `min(lvl) = 3 + lvl`, `max(lvl) = 6 + 2*lvl`.
- **On ally / charmed enemy**: self-damage = `round(curUser.HT * 0.05)`; healing = `selfDmg + 3*buffedLvl()`; if healing overflows max HP, the overflow becomes `Barrier` shield (`shielding = (HP+healing) - HT`). Damages caster by `selfDmg` (unless `freeCharge` flag set from staff proc). Caster death from this is tracked as "death from friendly magic".
- **On enemy (living)**: grants caster a self-`Barrier` shield of `5 + buffedLvl()`, and applies `Charm` to the enemy for `Charm.DURATION/2` (charm references caster as `object`, `ignoreHeroAllies=true`).
- **On undead enemy**: instead deals `damageRoll()` damage (Burning sound, shadow particles) — no charm.
- **Melee staff proc** (`onHit`): if defender is charmed by attacker, grants a free wand use (`freeCharge=true`) and shields attacker for `round(2*(5+buffedLvl()) * procChanceMultiplier(attacker))`.
- `upgradeStat1/2/3`: self-damage (`5%` of max HP, doesn't scale with level), healing (`selfDmg + 3*lvl`), shield (`5+lvl`), and damage range (inherited).

#### WandOfCorruption
- Not a DamageWand. `corruptingPower = 3 + buffedLvl()/3`.
- `enemyResist` baseline:
  - Mimic/Statue: `1 + Dungeon.depth`
  - Piranha/Bee: `1 + depth/2`
  - Wraith: `(1 + scalingDepth/4) / 5` (wraiths ~5x harder)
  - Swarm (children): `1 + AscensionCorruptResist` (forced to `1+3` if base is 1)
  - default: `1 + AscensionCorruptResist(enemy)`
- Then `enemyResist *= 1 + 4*(HP/HT)^2` — full-health enemies are 5x harder to corrupt, 25%-health enemies ~1.25x.
- Existing debuffs reduce resist: MAJOR_DEBUFFS (Amok, Slow, Hex, Paralysis, +0%-weighted Daze/Dread/Charm/MagicalSleep/SoulMark/Corrosion/Frost/Doom) → `*= 0.5`; MINOR_DEBUFFS (Weakness, Vulnerable, Cripple, Blindness, Terror, +0%-weighted Chill/Ooze/Roots/Vertigo/Drowsy/Bleeding/Burning/Poison) or any other NEGATIVE buff → `*= 0.75`.
- If already `Corruption`'d or `Doom`'d: forces `corruptingPower = enemyResist - 0.001` (guarantees debuff branch, not re-corrupt).
- If `corruptingPower > enemyResist`: **corrupt** — `Corruption.corruptionHeal(enemy)` then `AllyBuff.affectAndLoot(enemy, curUser, Corruption.class)` (enemy becomes ally, drops loot); if immune to Corruption, applies `Doom` instead.
- Else: roll `debuffChance = corruptingPower/enemyResist`; if hit → MAJOR debuff, else MINOR debuff (random weighted by category map, escalating a tier if all options exhausted/immune), duration `6 + buffedLvl()*3`.
- **Melee staff proc**: `procChance = (lvl+1)/(lvl+6) * procChanceMultiplier` → 16%/28.5%/37.5% at lvl 0/1/2; applies `Amok` for `round((4+lvl*2) * max(1,procChance))` turns.

#### WandOfRegrowth
- Not a DamageWand. `chargesPerCast()`: cursed or target has `WildMagicTracker` → 1; else `gate(1, ceil(curCharges*0.3), 3)` — consumes 30% of current charges (1–3).
- `fx`: `ConeAOE` with `maxDist = 2 + 2*chargesPerCast()` (4/6/8 tiles), angle `20 + 10*chargesPerCast()` degrees, `STOP_SOLID|STOP_TARGET`.
- `onZap`:
  - `grassToPlace = round((3.67 + buffedLvl()/3) * chargesPerCast())`.
  - Cells with chars get `Roots` for `4 * chargesPerCast()` turns + `wandProc`.
  - Eligible terrain (EMPTY/EMBERS/EMPTY_DECO/GRASS/HIGH_GRASS/FURROWED_GRASS, no immovable char, no plant) converted to `HIGH_GRASS` (or `FURROWED_GRASS` if over the charge-degradation threshold, chance `(chargesOverLimit+1)/5`).
  - If `chargesPerCast() >= 3`: spawns a `Lotus` NPC (HP=`25+3*lvl`, range=`lvl`, seed preservation `min(1, 0.4+0.04*lvl)`).
  - 16%/33%/50% chance (`Random.Int(6) < chrgUsed`) to plant a Seedpod or Dewcatcher.
  - 33%/66%/100% chance (`Random.Int(3) < chrgUsed`) to plant a random Generator seed.
- **Charge limit / degradation**: `chargeLimit(heroLvl, wndLvl)`:
  - `wndLvl >= 10` → unlimited (`∞`).
  - Else `round(20 + heroLvl * (2+wndLvl) * (1 + wndLvl/(50-5*wndLvl)))` — per-hero-level charges available before degradation (≈2/3.1/4.2/5.5/6.8/8.4/10.4/13.2/18.0/30.8 per level at wand lvl 0–9).
  - Once `totChrgUsed >= chargeLimit`, excess casts increase `chargesOverLimit`, raising `furrowedChance` (worse grass) by `(chargesOverLimit+1)/5`.
- **Melee staff proc**: if either combatant stands on grass/high-grass/furrowed-grass, heal attacker via `Sungrass.Health` buff for `round(damage * (lvl+2)/(lvl+6)/2 * procChanceMultiplier)` — 16%/21%/25% of half-damage at lvl 0/1/2.
- Sub-entities: `Dewcatcher` (plant, drops 3–6 `Dewdrop`s on activate to neighbouring passable cells excluding entrance/exit), `Seedpod` (plant, drops 2–4 random seeds), `Lotus` (NPC, neutral/immovable/static, decays 1 HP/turn, immune to Doom and all damage/buffs, blocks fog).
