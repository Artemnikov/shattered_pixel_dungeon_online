# Shattered Pixel Dungeon — Armor & Health Balance Reference

> Source analysis from `../shattered-pixel-dungeon/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/`
> Primary files: `actors/Char.java`, `actors/hero/Hero.java`, `items/armor/Armor.java`, `actors/buffs/Regeneration.java`, `actors/buffs/ShieldBuff.java`

---

## 1. Player Health System

### 1.1 Base Stats

| Stat | Level 1 | Per Level | Level 30 |
|------|---------|-----------|----------|
| HT/HP | 20 | +5 | 165 |
| STR | 10 | 0 | 10* |
| Attack Skill | 10 | +1 | 39 |
| Defense Skill | 5 | +1 | 34 |

\* STR only increases via Ring of Might (+1/level), Adrenaline Surge buff, or Strongman talent (+3–5% of base STR).

### 1.2 Max HP Calculation (`Hero.java:254`)

```
HT = 20 + 5 * (lvl - 1) + HTBoost           // base formula
HT *= pow(1.035, ringOfMightLevel)           // Ring of Might multiplier
HT += elixirOfMightBoost                     // +10 per Elixir of Might
HP = min(HP, HT)                             // clamp after boost
```

Ring of Might multiplier examples:

| Ring Level | Multiplier |
|-----------|-----------|
| +0 | 1.000× |
| +3 | 1.109× |
| +6 | 1.229× |
| +10 | 1.411× |

### 1.3 Passive Regeneration (`Regeneration.java`)

```
Base: 1 HP every 10 turns

Chalice of Blood (uncursed):
  delay = 10 - (1.33 + chaliceLvl * 0.667)
  delay /= RingOfEnergy.artifactChargeMultiplier

Chalice of Blood (cursed): delay *= 1.5

Salt Cube: delay /= healthRegenMultiplier

Disabled when:
  - Starving (hunger > 450)
  - LockedFloor buff present (boss arenas)
  - VaultLevel
```

Fractional HP accumulation prevents waste: `partialRegen += 1/delay` each tick.

### 1.4 Starvation (`Hunger.java`)

```
Hungry threshold:  300  (movement speed penalty)
Starving threshold: 450
Starvation damage:  HT / 1000  per turn  (~0.165 HP/turn at lvl 30)
```

### 1.5 Shield System (`ShieldBuff.java`)

Shields act as temporary HP buffers consumed **after** all other damage reduction. Priority determines consumption order:

| Priority | Source | Notes |
|----------|--------|-------|
| 2 | Warrior's Broken Seal, Blocking enchant | Fast-refreshing layer |
| 1 | Cleric's Ascended Form | Short-duration, moderate |
| 0 | Generic Barrier (wands, items, etc.) | Default |
| -1 | Berserk shield | Consumed last |

**Consumption algorithm** (`ShieldBuff.processDamage()`):
```
Sort shields by priority descending
for each shield with shielding > 0:
    if shielding >= dmg:  dmg = 0, break
    else:                 dmg -= shielding, continue
```

**Barrier decay**: `min(1, shielding / 20)` per turn. Modified by HoldFast talent (can reach 0 decay rate).

---

## 2. Armor System

### 2.1 Tier Availability

| Tier | Armor | Starting Floor | Base STR | DR Min | DR Max |
|------|-------|---------------|----------|--------|--------|
| 1 | Cloth | 1 | 10 | 0 | 2 |
| 2 | Leather | 1–4 | 12 | 0 | 4 |
| 3 | Mail | 6–9 | 14 | 0 | 6 |
| 4 | Scale | 11–14 | 16 | 0 | 8 |
| 5 | Plate | 16–19 | 18 | 0 | 10 |

### 2.2 STR Requirement Formula

```
STRReq(tier, upgradeLevel) = (8 + round(tier * 2)) - floor((sqrt(8 * lvl + 1) - 1) / 2)
```

Requirements drop at upgrade levels +1, +3, +6, +10 (triangular number sequence). Mastery Potion reduces STR requirement by 2.

### 2.3 Damage Reduction Formulas (`Armor.java:379-407`)

**DRMax:**
```
DRMax(lvl) = tier * (2 + lvl) + augment.defenseFactor(lvl)

// Overscale protection (only triggers when lvl > DRMax, rare):
if lvl > DRMax:  return (lvl - DRMax + 1) / 2
```

**DRMin:**
```
int max = DRMax(lvl)
if lvl >= max:  return lvl - max
else:           return lvl
```

**Key property**: `DRMin = upgrade level` (capped at DRMax). Upgrades always guarantee a minimum damage reduction floor.

**Practical examples:**

| Armor | Upgrade | DR Min | DR Max |
|-------|---------|--------|--------|
| Cloth | +0 | 0 | 2 |
| Cloth | +3 | 3 | 5 |
| Cloth | +10 | 10 | 12 |
| Plate | +0 | 0 | 10 |
| Plate | +3 | 3 | 25 |
| Plate | +10 | 10 | 60 |

### 2.4 Armor Augment (`Armor.java:92-112`)

| Augment | Evasion Factor | Defense Factor |
|---------|---------------|---------------|
| EVASION | `+round((2+lvl)*2)` | `-round(2+lvl)` |
| DEFENSE | `-round((2+lvl)*2)` | `+round(2+lvl)` |
| NONE | 0 | 0 |

### 2.5 Encumbrance Penalties (STR < STRReq)

```
Evasion:  evasion /= pow(1.5, deficit)      // -33%/point
Speed:    speed   /= pow(1.2, deficit)      // -17%/point
Armor DR:  DR     -= 2 * deficit            // -2 flat/point
Weapon DR: DR     -= 2 * deficit
```

Every missing STR point costs 2 DR + 33% evasion + 17% speed.

### 2.6 NO_ARMOR Challenge Mode

```
DRMax = 1 + tier + lvl + augment.defenseFactor(lvl)
DRMin = 0
```

Armor still equippable but provides minimal protection (no guaranteed DR floor).

---

## 3. Complete Damage Pipeline

### Step 0: Hit/Miss (`Char.java:624`)

```
acuRoll = Random.Float(attackSkill * accuracy)
defRoll = Random.Float(defenseSkill * evasion)

// Buff modifiers applied to both:
Bless   → *1.25
Hex     → *0.8
Daze    → *0.5
Champion → * evasionAndAccuracyFactor
Ascension → * statModifier
Talent.BLESS (allies) → *1.03–1.05
Ferret Tuft → * evasionMultiplier (defender only)

Hit if: acuRoll >= defRoll
```

Special rules: invisible = guaranteed hit; Monk Focus = guaranteed miss (miss beats hit).

### Step 1: Base Damage Roll

```
dmg = weapon.damageRoll()
    + RingOfForce.armedDamageBonus()    // if melee & unarmed
    + PhysicalEmpower.dmgBoost
    + Weapon Recharging talent          // *1.025 + 0.025*talentPts
```

### Step 2: Damage Multipliers (pre-DR, applied in `attack()`)

Applied in this exact order, multiplicatively (except where noted):

| # | Source | Multiplier | Notes |
|---|--------|-----------|-------|
| 1 | dmgMulti param | `* value` | passed from caller |
| 2 | dmgBonus param | `+ value` | flat additive, then multiplied |
| 3 | Searing Light | `+ (1 + 2*tier)` | flat additive |
| 4 | Berserk | `min(1.5, 1 + power/2)` | power max ~1.167 |
| 5 | Fury | `* 1.5` | |
| 6 | Power of Many | `* 1.25` | or `* 1.3–1.35` with Beaming Ray |
| 7 | Champion enemy | `* meleeDamageFactor` | |
| 8 | Ascension Challenge | `* statModifier(attacker)` | can be 0.1–10× |
| 9 | Endure (friendly) | `* damageFactor` | |
| 10 | Endure (enemy) | `adjustDamageTaken()` | reduces incoming |
| 11 | Challenge Arena | `* 0.67` | |
| 12 | Aura of Protection | `* 0.9 to 0.7` | based on talent pts |
| 13 | Meditate | `* 0.2` | |
| 14 | Weakness | `* 0.67` | |
| 15 | Aggression vs bosses | `* 0.5` | `* 0.25` vs Yog-Dzewa |

### Step 3: Defense Proc (`Hero.java:1538`)

```
1. Berserk damage tracking (builds rage)
2. Armor.glyph.proc()          → Thorns, Viscosity, Stone, etc.
3. Body Form glyph              → if unarmored
4. Holy Ward blocking           → -1 flat (-3 as Paladin)
5. Rock Armor                   → absorbs from stored pool
6. Earthroot                    → -min(damage, (depth+5)/2)
7. Shield of Light              → -Random.NormalIntRange(1+pts, 2*(1+pts))
```

**Important**: `defenseProc()` returns modified damage. A **negative return** skips armor DR entirely (some glyphs e.g. Affection, Repulsion can cause this via enemy displacement/movement).

### Step 4: Damage Reduction — DR Roll

Calculated in `attack()` at line 386:
```
dr = round(enemy.drRoll() * AscensionChallenge.statModifier(enemy))
```

**Hero's `drRoll()`** (`Hero.java:637`):
```
dr = Random.NormalIntRange(0, barkskinLevel)           // Barkskin
   + Random.NormalIntRange(DRMin(), DRMax())            // Armor DR
   - 2 * max(0, armorSTRReq - STR)                     // STR penalty
   + Random.NormalIntRange(0, weapon.defenseFactor())   // Weapon DR
   - 2 * max(0, weaponSTRReq - STR)                    // STR penalty
   + Random.NormalIntRange(talent, 2*talent)            // HoldFast
```

All DR components clamped to ≥0 before summing.

**DR bypasses**:
- **Sniper** ranged missile attacks (non-adjacent): `dr = 0`
- **Monk** unarmed ability attacks: `dr = 0`

### Step 5: Viscosity Deferral

```
// Applied if enemy has ViscosityTracker buff
deferredPercent = (level+1) / (level+6) * procChanceMultiplier
if deferredPercent > 1:  attacker takes full damage, defender takes reduced
else:  deferred = ceil(damage * deferredPercent), applied as DoT (10%/tick, min 1)
```

### Step 6: Vulnerable Multiplier

```
if Vulnerable debuff: effectiveDamage *= 1.33
```

Applied **after** DR so it can't be mitigated by armor.

### Step 7: Attack Proc (Weapon Enchantments)

```
effectiveDamage = attackProc(enemy, effectiveDamage)
```

Weapon enchantments (Blazing, Grim, Vampiric, etc.) and talent on-attack procs.

### Step 8: Final Damage Application (`Char.java:812`)

```
1. LifeLink damage sharing:        dmg /= links.size() + 1
2. Aura of Protection (non-Char):  dmg *= 0.9 - 0.1*talent
3. Power of Many (ally):           dmg *= 0.75 (or 0.70-0.05*talent with Life Link)
4. Doom:                           dmg *= 1.67
5. Death Mark:                     dmg *= 1.25
6. Sickle bleed conversion:        converts damage to Bleeding DoT, returns early
7. Resistances:                    dmg *= 0.5 per matching property resistance
8. Champion damage taken:          ceil(dmg * buff.damageTakenFactor())
9. AntiMagic:                      dmg -= AntiMagic.drRoll(this, glyphLevel)
10. ArcaneArmor:                   dmg -= Random.NormalIntRange(0, level)
11. Warrior Shield auto-activation: triggers if HP ≤ HT/2 (cooldown 150 turns)
12. Shield absorption:             ShieldBuff.processDamage() — consumes shields in priority order
13. HP -= dmg
14. Grim execution check:          chance = maxChance * ((HT-HP)/HT)^2
15. Kinetic damage tracking:       conserved on kill
```

### Step 9: Hero-Specific Post-Processing (`Hero.java:1580`)

```
// Only for non-Char damage sources:
if src is not Char:
    Endure.adjustDamageTaken()
    ChallengeArena: *0.67
    Meditate: *0.2

Cape of Thorns proc
Iron Stomach:          dmg /= 4 (tier 1), dmg = 0 (tier 2)
Ring of Tenacity:      ceil(dmg * pow(0.85, ringBonus * missingHP/HT))
super.damage(dmg, src) → Step 8
```

---

## 4. Weapon Defense Factors

| Weapon | Tier | Formula | +0 | +3 | +10 |
|--------|------|---------|----|----|-----|
| Greatshield | 5 | `6 + 2*lvl` | 6 | 12 | 26 |
| Round Shield | 3 | `4 + lvl` | 4 | 7 | 14 |
| All others | — | `0` | 0 | 0 | 0 |

---

## 5. Ring Effects on Balance

### 5.1 Ring of Tenacity

```
damageMultiplier = pow(0.85, ringBonus * missingHP / HT)
```

| Ring | 50% HP | 25% HP | 10% HP |
|------|--------|--------|--------|
| +1 | 0.922 (7.8%) | 0.884 (11.6%) | 0.864 (13.6%) |
| +3 | 0.783 (21.7%) | 0.691 (30.9%) | 0.645 (35.5%) |
| +6 | 0.614 (38.6%) | 0.474 (52.6%) | 0.374 (62.6%) |

Snowballs with missing HP — designed as a dramatic comeback mechanic.

### 5.2 Ring of Might

```
STR bonus:  +1 per ring level
HT multiplier:  pow(1.035, ringLevel)
```

---

## 6. Key Class/Subclass Balance Interactions

### 6.1 Warrior

```
Broken Seal shield:
  maxShield = 3 + 2*tier + talentPoints(IRON_WILL)
  activates when HP ≤ HT/2
  cooldown: 150 turns of regen
  auto-drains when no enemies visible for 5+ turns (50% cooldown refund)

Berserker:
  shieldFormula = (8 + 2*armorLevel) * (1 + 2*(1 - HP/HT)^3)
  range: 8 (100% HP) to 84 (0% HP, +10 armor)
  damageFactor = min(1.5, 1 + power/2)  // damage dealt multiplier
```

### 6.2 Huntress (Sniper)

```
Ranged missile attacks from non-adjacent position: enemy dr = 0
```

### 6.3 Monk

```
Unarmed ability attacks: enemy dr = 0
Meditate: all incoming damage * 0.2
```

### 6.4 Cleric

```
Power of Many (ally): damage * 0.75
Holy Ward: -1 flat damage (-3 as Paladin)
Aura of Protection: damage * (0.9 - 0.1*talentPoints)
```

### 6.5 Duelist

```
Combined Lethality: instant-kill threshold at ≤40% HP (with 3 talent pts) on non-boss/miniboss
```

---

## 7. Complete Balance Constants Reference

| Constant | Value |
|----------|-------|
| Starting HP/HT | 20 |
| HP per level | +5 |
| Max level | 30 |
| Base regen delay | 10 turns |
| Chalice regen delay | `10 - (1.33 + lvl*0.667)` |
| Regen cap | HT |
| Starvation damage | `HT / 1000` per turn |
| Blessed ankh revive | `HT / 4` |
| Earthroot blocking | `(depth + 5) / 2` |
| Sniper DR bypass | all DR at range |
| Vulnerable multiplier | `* 1.33` (post-DR) |
| Doom multiplier | `* 1.67` |
| Death Mark multiplier | `* 1.25` |
| Weakness multiplier | `* 0.67` |
| Challenge Arena multiplier | `* 0.67` |
| Resistance per property | `* 0.5` |

---

## 8. Design Patterns & Observations

### 8.1 Two-Pass Reduction

Damage passes through `defenseProc()` (glyphs/abilities) **before** the DR roll, then goes through `damage()` (resistances/shields) after. Different reductions in each pass:

```
Pre-DR (defenseProc):
  → glyph procs (Thorns reflects, Viscosity defers, Stone converts evasion)
  → Holy Ward flat reduction
  → Rock Armor / Earthroot absorbs
  → Shield of Light flat reduction

Post-DR (damage):
  → resistances (*0.5 per property)
  → AntiMagic (magic only)
  → shields (absorption)
```

### 8.2 DR Convergence with Upgrades

Upgrades make DR increasingly predictable. At +10, even Cloth guarantees 10 DR. The gap between DRMin and DRMax shrinks proportionally for lower tiers but stays wide for Plate.

### 8.3 STR Gating

STR requirements (10/12/14/16/18 for tiers 1–5) are the primary gating mechanism. With base STR=10 and only +STR coming from rare items, early access to high-tier armor is impossible without sacrificing optimal stat allocation or using Mastery Potions.

### 8.4 Comeback Multipliers

Multiple systems scale with missing HP:

1. **Berserk shield**: `(1 + 2*(1 - HP/HT)^3)` grows rapidly at low HP
2. **Ring of Tenacity**: `pow(0.85, bonus * missingHP/HT)` provides increasing % reduction
3. **Endure**: damage factor improves at low HP
4. **Grim enchant**: `chance = maxChance * ((HT-HP)/HT)^2` grows quadratically

### 8.5 DR Bypass Design

Sniper and Monk bypass enemy DR entirely — this is a deliberate class balance lever to keep ranged characters competitive against high-armor enemies and monk viable as a low-equipment class.

### 8.6 Shield Priority Architecture

Higher-priority shields (Warrior seal, Blocking) absorb first to absorb burst. Lower-priority shields (Barrier, Berserk) absorb last, acting as a last line of defense. Berserk shield at priority -1 ensures it's always the very last shield consumed.

### 8.7 Viscosity–Regeneration Synergy

Viscosity converts burst damage into a slow DoT (10% per tick). This strongly synergizes with passive HP regeneration, making deferred damage effectively free over time — but is useless against one-shot kills.

### 8.8 Encumbrance Curve

STR deficit penalties are steep: -33% evasion and -2 DR per missing point. This creates a sharp power cliff — 1 point under is inconvenient, 2 points under is painful, 3+ is crippling. This forces meaningful upgrade/equipment choices rather than simply equipping the best armor regardless of STR.
