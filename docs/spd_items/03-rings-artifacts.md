# SPD Rings & Artifacts Spec

Source: `core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/{rings,artifacts}/`
Names/descriptions: `core/src/main/assets/messages/items/items.properties` (keys `items.rings.*`, `items.artifacts.*`)

## Equip slots

A character has 3 "misc" slots resolved by `KindofMisc`: one `ring` slot (any `Ring`), one `artifact` slot (any `Artifact`), and one generic `misc` slot that can hold a second ring OR second artifact (but not e.g. trinkets at the same time — `misc` is shared). So at most **2 rings + 2 artifacts** can be worn simultaneously (1 in dedicated slot + 1 in shared misc slot each).

---

## 1. Ring base class (`Ring.java`)

### Identification
- Rings are NOT identified by "use" — identification accrues via hero XP while equipped: `levelsToID -= levelPercent * Talent.itemIDSpeedFactor(hero, this)`. Starts at `1.0`; once `<= 0`, ring auto-identifies (or becomes "ready to identify" if `ShardOfOblivion` passive-ID is disabled).
- Each of the 12 ring types is assigned a random gem appearance (`garnet, ruby, topaz, emerald, onyx, opal, tourmaline, sapphire, amethyst, quartz, agate, diamond`) per seed via `ItemStatusHandler`.

### Random generation (`random()`)
- Level distribution: +0 = 66.67% (2/3), +1 = 26.67% (4/15), +2 = 6.67% (1/15)
- 30% chance to spawn cursed (`cursed = true`)

### Upgrading
- `upgrade()`: standard `level++`; additionally **1/3 chance to remove curse** on upgrade (`Random.Int(3) == 0 → cursed = false`)

### Value (shop price)
```
price = 75
if cursed && cursedKnown: price /= 2
if level() > 0: price *= (level()+1)
if level() < 0: price /= (1 - level())
min price = 1
```

### Core bonus formulas
For an individual ring instance:
- `soloBonus()`:
  - if cursed: `min(0, level() - 2)` (i.e. +0 cursed → -2, +1 cursed → -1, +2 cursed → 0, +3+ cursed → 0)
  - else: `level() + 1`
- `soloBuffedBonus()`: same formula but using `buffedLvl()` instead of `level()`
- `buffedLvl()` = `level()` + 1 if hero has `EnhancedRings` buff (Cleric's Empowered/Divine Inspiration effect), else `level()`

### Aggregate bonus across worn rings
- `Ring.getBonus(target, RingBuffClass)` = sum of `level()` (soloBonus equivalent via buff's `level()`) over all attached `RingBuff`s of that type
- `Ring.getBuffedBonus(target, RingBuffClass)` = sum of `buffedLvl()` over all attached `RingBuff`s of that type
- If target has `MagicImmune`, both return 0
- **Spirit Form** (Warlock spell): if the hero has 0 bonus from worn rings but is in Spirit Form and the Spirit Form's "ring" matches the queried buff class, contributes that ring's `soloBonus()`/`soloBuffedBonus()` as if worn (lets Warlocks use one ring's effect while spirit-formed without wearing it)
- `combinedBonus(hero)` / `combinedBuffedBonus(hero)`: sums `soloBonus()`/`soloBuffedBonus()` across BOTH the `ring` slot item and `misc` slot item if they are the same ring class — used purely for displaying "if you wore 2 of this ring" info text

### Two of the same ring stacking
Each worn `RingBuff` instance contributes its own `soloBonus()` independently — i.e. two Ring of Haste +0 each contribute `+1` for a total `+2` effective level passed into the exponential formulas (multiplicative stacking of the two `1.175^1` factors via summed exponents = `1.175^2`).

---

## 2. All 12 Rings — Effect Formulas

Formula variable `L` = `getBuffedBonus(target, RingBuff)` (summed `soloBuffedBonus()` across all worn copies of that ring, generally `level()+1` per ring unless cursed).

| Ring | Internal name | Effect | Formula | +0 effect | Notes |
|---|---|---|---|---|---|
| **RingOfAccuracy** | `Accuracy` | Multiplies accuracy | `1.3^L` | +30% | `accuracyMultiplier(target)` |
| **RingOfArcana** | `Arcana` | Multiplies weapon enchant/glyph activation chance & power | `1.175^L` | +17.5% | `enchantPowerMultiplier(target)`; affects curses too |
| **RingOfElements** | `Resistance` | Resistance multiplier vs. elemental/status effects | `0.825^L` (damage/duration multiplier, lower=better) | -17.5% effect | `resist(target, effectClass)`; only applies if effect class is in `RESISTS` set (Burning, Chill, Frost, Ooze, Paralysis, Poison, Corrosion, ToxicGas, Electricity, + AntiMagic.RESISTS) |
| **RingOfEnergy** | `Energy` | Recharge speed multiplier for wands/artifacts/armor abilities | `1.175^L` | +17.5% | Separate multipliers: `wandChargeMultiplier`, `artifactChargeMultiplier`, `armorChargeMultiplier`. Wand/artifact multipliers get extra boost from Cleric/Rogue talents (`LIGHT_READING`/`LIGHT_CLOAK`) for non-Cleric/Rogue: `*= 1 + 0.2*(points/3)` |
| **RingOfEvasion** | `Evasion` | Evasion multiplier | `1.125^L` | +12.5% | `evasionMultiplier(target)` |
| **RingOfForce** | `Force` | Acts as a weapon-tier bonus for unarmed combat (see below) | special | T1 weapon-equivalent at +0 | Also grants Duelist's Brawler's Stance ability |
| **RingOfFuror** | `Furor` | Attack speed multiplier | `1.09051^L` | +9.051% | `attackSpeedMultiplier(target)` |
| **RingOfHaste** | `Haste` | Movement speed multiplier | `1.175^L` | +17.5% | `speedMultiplier(target)` |
| **RingOfMight** | `Might` | +STR and +Max HP | STR: `getBonus(target,Might)` (unbuffed); HT: `1.035^L` | +1 STR, +3.5% HT | `strengthBonus`, `HTMultiplier`; triggers `hero.updateHT()` on equip/unequip/level |
| **RingOfSharpshooting** | `Aim` | +flat damage to projectiles (level-based) & projectile durability | dmg bonus = `getBuffedBonus` (unscaled int); durability = `1.2^soloBonus` | +1 dmg, +20% durability | `levelDamageBonus`, `durabilityMultiplier` (durability uses unbuffed bonus) |
| **RingOfTenacity** | `Tenacity` | Reduces incoming damage as HP drops (emergency mitigation) | `0.85 ^ (L * (HT-HP)/HT)` | up to -15% dmg at L=1 at 0 HP | `damageMultiplier(t)`; multiplier approaches 1 (no effect) at full HP, approaches `0.85^L` at 0 HP |
| **RingOfWealth** | `Wealth` | Increases loot drop chance from enemies/containers + bonus drop system | drop chance mult = `1.2^L` | +20% | See "Ring of Wealth bonus drops" below |

### RingOfForce details (weapon-tier formula)
```
tier(STR) = max(1, (STR-8)/2)   // capped: tier>5 → 5 + (tier-5)/2
min(lvl, tier) = round(tier + lvl)              // lvl<=0 forces tier=1
max(lvl, tier) = round(5*(tier+1) + lvl*(tier+1))
```
- If hero is unarmed (no weapon, no thrown/ability weapon) and has Ring of Force equipped: unarmed damage = `damageRoll in [min(L,tier), max(L,tier)]` where `L = getBuffedBonus(hero, Force)`
- If unarmed WITHOUT ring of force: damage = `[1, max(STR-8, 1)]`
- Cursed/level<=0: `tier` forced to 1 for min/max calc
- **Duelist interaction**: equipping Ring of Force grants `MeleeWeapon.Charger` buff and unlocks "Brawler's Stance" ability (`BrawlersStance` buff). While active for ≥50 turns minimum, adds bonus unarmed damage: `bonus = round(3 + tier + L*((4+2*tier)/8))`. Unequipping the ring (with no other Force ring) clears the stance.
- `fightingUnarmed()`, `unarmedGetsWeaponEnchantment()`, `unarmedGetsWeaponAugment()` — gate whether Force/Brawler's-Stance unarmed attacks inherit the equipped weapon's enchant/augment.

### RingOfMight details
- `strengthBonus(target)` = unbuffed `getBonus(target, Might)` — adds directly to effective STR for equip requirements
- `HTMultiplier(target)` = `1.035^L` — multiplies hero's max HP (applied via `hero.updateHT()`)
- Equip/unequip/level-change all call `hero.updateHT(false)`

### RingOfWealth bonus drops
- `dropChanceMultiplier = 1.2^L` increases base "lootChance" rolls on mobs/containers elsewhere in the codebase
- **Separate bonus-drop system** via `tryForBonusDrop(target, tries)`:
  - Uses two persistent counters: `TriesToDropTracker` (random init `NormalIntRange(0,20)`) and `DropsToEquipTracker` (random init `NormalIntRange(5,10)`)
  - Each call decrements `triesToDrop` by `tries`; whenever it hits ≤0, a drop is generated and `triesToDrop` resets to `+NormalIntRange(0,20)`
  - Drop type alternates: if `dropsToEquip <= 0` → equipment drop (`genEquipmentDrop`), resets `dropsToEquip += NormalIntRange(5,10)`; else → consumable drop (`genConsumableDrop`), decrements `dropsToEquip`
  - **Consumable drop tiers** (`genConsumableDrop(level)`, `level = buffedBonus-1`):
    - 60% - 4%*level → low tier (half-stack gold / stone / potion / scroll)
    - next 30% + 2%*level → mid tier (doubled low-tier, or exotic potion/scroll, unstable brew/spell, bomb, honeypot)
    - remaining 10% + 2%*level → high tier (doubled mid-tier / stone of enchantment / potion of experience or divine inspiration / scroll of transmutation or metamorphosis)
  - **Equipment drop** (`genEquipmentDrop(level)`): `floorset = (depth+level)/5`; 40% weapon, 20% armor, 20% ring, 20% artifact. Item gets enchant/glyph if `Random.Int(10) < level` (else strips curse). Minimum `level()` on result = `(level+1)/2`. `cursed=false, cursedKnown=true` always.
  - **Two rings of wealth cap**: when computing `equipBonus` for equipment drops, a second equipped Ring of Wealth contributes at most `+2` to the bonus (anti-farming measure)

---

## 3. Artifact base class (`Artifact.java`)

### Common mechanics
- `levelCap` — per-artifact max level (varies: 3, 5, or 10)
- `exp` — internal experience counter driving level-ups (per-artifact thresholds)
- `charge` / `chargeCap` / `partialCharge` — current/max charge and fractional accumulator
- `cooldown` — generic per-artifact cooldown counter
- `visiblyUpgraded()` = `round(level()*10 / levelCap)` — always shown as a 0-10 scale regardless of actual `levelCap`, when `levelKnown`
- `buffedLvl()` = `level()` (artifacts unaffected by buffs/debuffs)
- Two equipment slots can't both hold the same artifact class (`cannot_wear_two`)
- `random()`: always spawns at +0; 30% chance cursed
- `value()`: `100 + 20*visiblyUpgraded()`, halved if cursed & cursedKnown, min 1
- `status()` display priority: cooldown (if≠0) → `chargeCap==100` as `%` → `chargeCap>0` as `charge/chargeCap` → raw `charge` if nonzero → null
- `charge(Hero, amount)` — generic hook subclasses override to convert "charge input" (from Hero's regen tick, scaled by level/turns) into artifact-specific charge/exp gains
- `transferUpgrade(transferLvl)` / `resetForTrinity(visibleLevel)` — support for the Well of Transmutation / Trinity item-swap mechanic; converts the 0-10 visible scale back to the artifact's actual `levelCap` scale

### `artifactProc(target, artifLevel, chargesUsed)` — shared on-hit hook
Called by several artifacts when they affect an enemy. Triggers:
- **Priest**: if target has `GuidingLight.Illuminated`, detach it and deal `5 + hero.lvl` damage
- **Searing Light talent** (non-Cleric): if target is an enemy and `SearingLightCooldown` not active, apply `Illuminated` to target and 20-turn cooldown to hero
- **Sunray talent** (non-Cleric): 15%/25% chance (scaling with talent points) to apply 4-turn Blindness to target

---

## 4. All 13 Artifacts

### 4.1 AlchemistsToolkit (`alchemiststoolkit`)
- **Level cap**: 10. **Charge**: energy units (no fixed cap — accumulates freely)
- **Warm-up**: on equip, `warmUpDelay = 101`. Each turn while warming: at level 10 instantly 0; else `warmUpDelay -= 100 / (10-level())^2` (turns to warm = `(10-level)^2`)
- **Passive charge gain** (`kitEnergy.gainCharge`): `chargeGain = (2 + level()) * levelPortion * RingOfEnergy.artifactChargeMultiplier`. "levelPortion" = fraction of a hero level gained. Charge increments by whole integers (1 energy units).
- **Actions**:
  - `BREW` — opens the Alchemy Scene (brewing potions/exotic items) using `charge` as the energy pool
  - `ENERGIZE` (only if `level() < 10`) — costs 6 `Dungeon.energy` per artifact level gained; lets player spend up to `min(levelCap-level, Dungeon.energy/6)` levels at once
- **Cursed**: cannot brew or energize

### 4.2 ChaliceOfBlood (`chaliceofblood`)
- **Level cap**: 10. Sprite changes at level≥2 (`CHALICE2`) and ≥6 (`CHALICE3`)
- **Active: "Prick" (AC_PRICK)** — self-damage to upgrade:
  - `minPrickDmg = ceil(3 + 2.5*level^2)`, `maxPrickDmg = floor(7 + 3.5*level^2)`
  - Damage rolled `NormalIntRange(min,max)`, reduced by armor/rock-armor absorb and `drRoll()`; min 1 damage dealt
  - Shows death-chance estimate before confirming (based on hero's current HP+shield vs max possible damage)
  - On survival: `upgrade()` (i.e., +1 level, increasing both prick damage AND healing — see below)
  - On death: counts as "death from friendly magic"
  - Unavailable while cursed or while hero `isInvulnerable`
- **Passive heal** (`charge()` → `chaliceRegen`, functions like extra `Regeneration`):
  - Only if not starving. `healDelay = (10 - (1.33 + level*0.667)) / amount`; `heal = 5/healDelay` (≈0.5/1/1.5/2/2.5 HP "per regen tick" at level 0/6/8/9/10), with probabilistic rounding for the fractional part
- **Cursed**: no prick action, no heal

### 4.3 CloakOfShadows (`cloakofshadows`)
- **Level cap**: 10. `unique=true`, `bones=false` (doesn't persist on death)
- **chargeCap** = `min(level()+3, 10)` (starts at 3, +1 per level up to 10 at level 7+)
- **Active: "Stealth" (AC_STEALTH)** — toggles `cloakStealth` buff (POSITIVE type):
  - Costs 1 charge per 4 turns of invisibility (`turnsToCost` ticks down from 4; on hitting 0, consumes 1 charge and resets to 4, or detaches if `charge` would go negative)
  - Grants `target.invisible++`; for Assassin subclass also applies `Preparation`; for `PROTECTIVE_SHADOWS` talent applies `ProtectiveShadowsTracker`
  - **Exp gain while active**: `lvlDiffFromTarget = hero.lvl - (1 + level*2)`, with extra `-1` per level beyond 6. If `>=0`: `exp += round(10 * 1.1^diff)`; else `exp += round(10 * 0.75^(-diff))`. Levels up at `exp >= (level+1)*50`
  - `dispel()` — forcibly consumes a charge and detaches if turn cost was already due
- **Passive recharge** (`cloakRecharge`): only while not active and `Regeneration.regenOn()`. `missing = chargeCap - charge` (+`5*(level-7)/3` extra if level>7). `turnsToCharge = (45 - missing) / RingOfEnergy.artifactChargeMultiplier`. `chargeToGain = 1/turnsToCharge`
- **LIGHT_CLOAK talent (Rogue subclass talent)**: lets non-equipped cloak passively activate for the hero; charge gain while unequipped scaled by `0.75 * pointsInTalent/3`
- **Cursed**: cannot activate stealth; `value() = 0` always (never sells)

### 4.4 DriedRose (`driedrose`) — Ghost companion
- **Level cap**: 10. `chargeCap = 100`. Sprite changes at level≥4 (`ROSE2`), ≥9 (`ROSE3`)
- **Gating**: requires `Ghost.Quest.completed()` (a quest line) before any artifact actions are available
- **Active: "Summon" (AC_SUMMON)** — requires `charge == 100`, not cursed, no ghost currently summoned:
  - Spawns `GhostHero` (a `DirectableAlly`) adjacent to hero, resets `charge = 0`
  - Ghost stats: `HT = 20 + 8*rose.level()`, `defenseSkill = hero.lvl + 4`, `attackSkill = hero.lvl + 9` (× weapon accuracy factor if equipped)
  - Ghost damage roll: equipped `weapon.damageRoll()` else `NormalIntRange(0,5)`
  - Ghost can be equipped with a hero-donated melee weapon/armor (via `AC_OUTFIT` → `WndGhostHero`), restricted by `ghostStrength() = 13 + level()/2` (STR requirement check)
  - Ghost is flying, undead/inorganic, immune to CorrosiveGas, Burning, Retribution scroll, Psionic Blast scroll, AllyBuff
  - Ghost dies permanently if hero unequips the rose or is `MagicImmune` (takes 1 dmg/turn as `NoRoseDamage`)
- **Active: "Direct" (AC_DIRECT)** — available whenever a ghost exists; lets player target a cell for the ghost to move/defend/attack via `DirectableAlly` mechanics
- **Passive charge** (`roseRecharge`):
  - While ghost is alive & not at full HP: heals ghost `(ghost.HT/500) * RingOfEnergy.artifactChargeMultiplier` HP-equivalent per regen tick (full heal over ~500 turns); rose itself does NOT charge while ghost lives
  - While no ghost: charges `1/5 * RingOfEnergy.artifactChargeMultiplier` per tick toward `chargeCap=100` (full charge ≈500 turns)
  - **Cursed**: 1% chance per tick to spawn a hostile `Wraith` near the hero instead of charging
- **`charge(target, amount)` override**: if no ghost, gains `4*amount` partial charge toward 100; if ghost exists and damaged, heals ghost `round((1 + level/3) * amount)` HP directly
- **Petal item** (`DriedRose.Petal`, stackable): picking one up calls `rose.upgrade()` (+1 level) up to `levelCap`
- Each `upgrade()`: increases `droppedPetals` tracker (max with current level), heals ghost +8 HP (capped at HT), updates ghost's HT via `updateRose()`

### 4.5 EtherealChains (`etherealchains`)
- **Level cap**: 5. **chargeCap**: soft cap `5 + level*2` (charge can exceed soft cap up to `2x` via passive regen, but exp-based charge gain is throttled past soft cap)
- **Active: "Cast" (AC_CAST)** — targets a cell; computes a `Ballistica` from hero to target:
  - **If an enemy occupies the collision point** (`chainEnemy`): pulls the enemy toward the hero along the chain path to the nearest valid empty tile. Cost = `distance(enemy.pos, pulledPos)` charge. Enemy with `IMMOVABLE` property cannot be pulled. Triggers `artifactProc`.
  - **If no enemy** (`chainLocation`): pulls the HERO toward the collision point, provided it's adjacent to a solid tile (a "grabbable" surface) and not a wall. Cost = `distance(hero.pos, newHeroPos)` charge. Hero must not be rooted.
  - Both consume charge equal to tiles traveled; dispel invisibility; `Talent.onArtifactUsed`
- **Passive recharge** (`chainsRecharge`):
  - Toward soft cap `5+level*2`: `chargeGain = 1/(40 - (chargeTarget-charge)*2) * RingOfEnergy.artifactChargeMultiplier`
  - **Cursed**: 1% chance per tick to apply 10-turn `Cripple` to hero
- **Exp gain** (`gainExp(levelPortion)`, called from hero leveling):
  - `exp += round(levelPortion * 100)`; if `charge > 5+level*2` (above soft cap), `levelPortion *= (5+level*2)/charge` (throttled)
  - `partialCharge += levelPortion * 6` (separate from `charge()`)
  - Levels up at `exp > 100 + level*100`, capped at `levelCap=5`
- **Trinity reset**: `charge = 5 + level*2` (soft cap)

### 4.6 HolyTome (`holytome`) — Cleric spellbook
- **Level cap**: 10. `unique=true`, `bones=false`
- **chargeCap** = `min(level()+3, 10)`
- **Active: "Cast" (AC_CAST)** — opens `WndClericSpells` to choose/cast a `ClericSpell`; spell cost is `spell.chargeUse(hero)` charges
- **canCast()** check: equipped (or `LIGHT_READING` talent owner carrying it), not MagicImmune, `charge >= spell cost`, and spell's own `canCast`
- **spendCharge(chargesSpent)**:
  - Decrements `partialCharge`/`charge` by `chargesSpent`
  - **Exp formula** (same shape as EtherealChains): `lvlDiffFromTarget = hero.lvl - (1 + level*2)`, extra `-1`/level beyond 6. If `>=0`: `exp += round(chargesSpent * 10 * 1.1^diff)`; else `round(chargesSpent * 10 * 0.75^-diff)`
  - Levels up at `exp >= (level+1)*50`
- **Passive recharge** (`TomeRecharge.act`): same shape as Cloak/Spellbook —
  - `missing = chargeCap - charge` (+`5*(level-7)/3` if level>7); `turnsToCharge = (45-missing)/RingOfEnergy.artifactChargeMultiplier`; `chargeToGain = 1/turnsToCharge`
  - If unequipped but hero has `LIGHT_READING` talent: `chargeToGain *= 0.75 * points/3`
- **Quick-spell**: can bind a `ClericSpell` to the action indicator for one-tap cast via `setQuickSpell`
- **LIGHT_READING talent**: non-Cleric classes can use the Tome passively without equipping it (in backpack)

### 4.7 HornOfPlenty (`hornofplenty`)
- **Level cap**: 10. **chargeCap** = `5 + level()/2` (5 at +0, up to 10 at +10). Sprite tiers by charge: `<2`→HORN1, `2-4`→HORN2, `5-7`→HORN3, `≥8`→HORN4
- **Actions**:
  - `EAT`/`SNACK` (if `charge > 0`): consumes hunger satiety. `satietyPerCharge = Hunger.STARVING/5` (or `/15` under NO_FOOD challenge). `EAT` consumes `max(1, hunger_deficit/satietyPerCharge)` charges (capped at available charge); `SNACK` always consumes exactly 1. Spends `Food.TIME_TO_EAT` (or `-2` with Iron Stomach / meal talents)
  - `STORE` (if `level() < 10`, not cursed): feed a `Food` item into the horn via `gainFoodValue`
- **gainFoodValue(food)** — converts food's `energy` (+ bonus: Pasty/PhantomMeat +`Hunger.HUNGRY/2`, MeatPie +`Hunger.HUNGRY`) into `storedFoodEnergy`. When `storedFoodEnergy >= Hunger.HUNGRY`, grants `floor(storedFoodEnergy/HUNGRY)` levels (capped at `10-level`), consumes that energy
- **Passive charge** (`hornRecharge.gainCharge`): `chargeGain = Hunger.STARVING * levelPortion * (0.25 + 0.125*level) * RingOfEnergy.artifactChargeMultiplier`, converted to charge units by `/(Hunger.STARVING/5)`. Stops at `chargeCap` (prints "full" message)
- **Cursed**: cannot store food (no level progression), but can still eat existing charge

### 4.8 MasterThievesArmband (`masterthievesarmband`)
- **Level cap**: 10. **chargeCap** = `5 + level/2` initially, but `upgrade()` recomputes as `5 + (level+1)/2`
- **Active: "Steal" (AC_STEAL)** — target an adjacent enemy mob (not shopkeeper, not neutral except hostile Mimics):
  - Costs 1 charge. `lootMultiplier = 1 + 0.1*level`; `debuffDuration = 3 + level/2`
  - If the attack surprises the target: `lootMultiplier += 0.5`, `debuffDuration += 2`, `exp += 2`, plays `Surprise.hit`
  - `lootChance = mob.lootChance() * lootMultiplier`; forced to 0 if `hero.lvl > mob.maxLvl + 2` or target already has `StolenTracker`
  - On success roll: generates `mob.createLoot()` and auto-pickups/drops it; sets `StolenTracker(true)`. On failure: `StolenTracker(false)`
  - Always applies `Blindness` and `Cripple` for `debuffDuration`; triggers `artifactProc`
  - `exp += 3` per use; levels up when `exp >= 10 + round(3.33*level)`
- **Passive theft from shops** (`Thievery.steal(item)`, used elsewhere e.g. shop browsing):
  - `chargesToUse(item)`: greedily consumes charge where each charge "covers" `10 + level/2` gold of value, up to `charge` available
  - `stealChance(item) = min(1, chargesUsed*(10+level/2) / item.value())`
  - On success: `charge -= chargesUsed`, `exp += 4*chargesUsed`, same level-up formula as above
- **Passive charge** (`Thievery.gainCharge`): `chargeGain = 3 * levelPortion * RingOfEnergy.artifactChargeMultiplier`
- **Cursed**: 20% chance/turn to lose 1 gold (`Dungeon.gold--`) if `Dungeon.gold > 0`; no steal action

### 4.9 SandalsOfNature (`sandalsofnature`)
- **Level cap**: 3 (lowest of all artifacts). **chargeCap = 100**
- Sprite/name progression: level -1→SANDALS(base), 0→SHOES, 1→BOOTS, 2-3→GREAVES; `name()` returns `name_<level>` variant strings
- **Seed absorption** (`AC_FEED`): feed a `Plant.Seed` item (one of 12 plant types, each with a distinct glow color and `seedChargeReqs`: Rotberry 8, Mageroyal/Fadeleaf/Blindweed 12, Firebloom/Swiftthistle/Icecap/Stormvine/Sorrowmoss 20, Earthroot/Starflower 40, Sungrass 80):
  - Each unique seed type absorbed is added to `seeds` list (max 3+3*level distinct seeds before level cap; at cap, re-feeding the SAME seed type just re-selects it)
  - Sets `curSeedEffect = seedClass` (becomes the "active" plant ability)
  - When `seeds.size() >= 3 + 3*level`: clears `seeds`, calls `upgrade()` (max level 3)
- **Active: "Root" (AC_ROOT)** — requires `curSeedEffect != null` and `charge >= seedChargeReqs[curSeedEffect]`:
  - Targets a cell within FOV and `distance <= 3`; couches/plants the seed's `Plant` there and activates it on any char present
  - Consumes `seedChargeReqs[curSeedEffect]` charge; triggers `artifactProc`
- **Passive charge** (`Naturalism.charge`, separate trigger — called when standing on grass): `chargeGain = (3+level)/6 * RingOfEnergy.artifactChargeMultiplier` (0.5 at +0 up to ~1 at +10, though level capped at 3 so max ~0.667)
- **Cursed**: no feed/root actions

### 4.10 SkeletonKey (`skeletonkey`)
- **Level cap**: 10. **chargeCap** = `3 + level/2` initially; `upgrade()` recomputes as `3 + (level+1)/2`
- **Active: "Insert" (AC_INSERT)** — target adjacent cell or distant wall:
  - **Locked door** (`Terrain.LOCKED_DOOR`, only if level not globally `locked`): costs 1 charge → opens to `DOOR`. `gainExp(2+1)`
  - **`HERO_LKD_DR`** (a door the hero locked themself): free, no charge, opens to `DOOR`, no exp
  - **Crystal door**: costs 5 charge → opens to `EMPTY` (removes wall entirely). `gainExp(2+5)`. Also removes "distant well" landmark note
  - **Open/closed normal door**: costs 2 charge → converts to `HERO_LKD_DR` (hero-locked, can be freely reopened later). Knocks back any char standing in the doorway via `WandOfBlastWave`. Scatters any item heap in the doorway to adjacent passable cells. `gainExp(2)`
  - **Locked chest** (`Heap.Type.LOCKED_CHEST`): costs 2 charge → opens. `gainExp(2+2)`
  - **Crystal chest**: costs 5 charge → opens. `gainExp(2+5)`
  - **Distant wall** (any other target, ≥2 charge required): summons temporary `KeyWall` blobs (10-turn duration, solid/LOS-blocking) around the hero in the direction away from target — pattern covers 3 or 5 cells depending on cardinal vs. diagonal direction. Knocks back any enemy caught in a wall cell. `gainExp(2)`
  - `LOCKED_EXIT` terrain and already-`locked` dungeon levels block the locked-door action entirely
- **gainExp(xpGain)**: `exp += xpGain`; levels up at `exp > 4+level`
- **Passive recharge** (`keyRecharge`): `chargeGain = 1/(120 - (chargeCap-charge)*7.5) * RingOfEnergy.artifactChargeMultiplier`
- **KeyReplacementTracker** (buff, `revivePersists`): tracks how many Iron/Golden/Crystal keys are still "needed" per depth after using the SkeletonKey to open locks normally requiring those keys — auto-discards excess keys from inventory/notes
- **Cursed**: no insert action

### 4.11 TalismanOfForesight (`talismanofforesight`)
- **Level cap**: 10. **chargeCap = 100**
- **Active: "Scry" (AC_SCRY)** — requires `charge >= 5`; targets a cell:
  - `maxDist = min(5 + 2*level, (charge-3)/1.08)` — enforces min distance 3 from hero, clamps target along the ballistic path to `maxDist`
  - Casts a cone (`ConeAOE`) from hero toward target: `angle = round(200 * 0.92^dist)` (200° at dist≈0, narrowing ~8%/tile)
  - For every cell in the cone: reveals fog (`mapped=true` if discoverable & unseen, `+1 exp` each), reveals secret doors/traps (`+10 exp` for secret traps, `+100 exp` for secret doors), and tags visible enemies/items with `CharAwareness`/`HeapAwareness` buffs (5+2*level turn duration) — `+10 exp` if char/heap wasn't previously seen
  - Enemies hit get `artifactProc(mob, level, chargeUsed≈3+dist*1.08)`
  - Charge cost: `3 + dist*1.08` (fractional, tracked via `partialCharge`)
  - Levels up at `exp >= 100 + 50*level`
- **Passive recharge** (`Foresight.act`): `chargeGain = (0.05 + level*0.005) * RingOfEnergy.artifactChargeMultiplier` (full charge in ~2000 turns at +0, ~1000 at +10)
- **Passive secret-trap detection** (`checkAwareness`): every turn, scans a 7x7 area around the hero for searchable secret traps within FOV; if found and not previously warned, shows "uneasy" message + interrupts hero (icon = `FORESIGHT`)
- **Cursed**: no scry action, no awareness warning

### 4.12 TimekeepersHourglass (`timekeepershourglass`)
- **Level cap**: 5. **chargeCap** = `5 + level` (5 at +0 up to 10 at +5)
- **Active (AC_ACTIVATE)** — prompts choice between two modes (only one `activeBuff` at a time):
  - **"Stasis"** (`timeStasis`, POSITIVE, lowest act priority so it ends turn last):
    - Consumes `min(charge, 2)` charge; grants that many "free turns": `spend(5*usedCharge)` to the hero, and restores `5*usedCharge` hunger satiety (no penalty)
    - Hero becomes invisible + paralyzed for the duration, then the buff self-detaches after acting once (effectively a multi-turn skip where nothing can act against the hero)
  - **"Freeze"** (`timeFreeze`, POSITIVE):
    - Immediately costs 1 charge; calls `artifactProc` on all visible mobs
    - `turnsToCost` starts at 2.0; `processTime(time)` subtracts elapsed time, consuming 1 charge per 2 turns elapsed (supports fractional time)
    - While active, **all other actors (mobs, traps, plants) are frozen** (`Emitter.freezeEmitters`, mobs get `PARALYSED` sprite state) — hero acts freely
    - Tracks `presses` (cells where hero stepped on traps/plants during freeze) — these are deferred and triggered (`triggerPresses`) or disarmed (`disarmPresses`, for non-Rotberry plants and disarmable traps) when freeze ends
    - Detaches automatically when `charge < 0` or `charge==0 && turnsToCost<=0`
- **Passive recharge** (`hourglassRecharge`): `chargeGain = 1/(90 - (chargeCap-charge)*3) * RingOfEnergy.artifactChargeMultiplier` (full in 90 turns at +0... 60 turns scaling toward higher levels)
  - **Cursed**: 10% chance/turn the hero loses a full turn (`hero.spend(TICK)`) instead of charging
- **Sandbag item** (`TimekeepersHourglass.sandBag`): pickup directly calls `hourglass.upgrade()` (+1 level, +1 chargeCap), tracked via `sandBags` counter for Trinity transfer
- **Trinity reset**: `charge = visibleLevel/2 - 1` (grants 4-10 turns of freeze depending on visible level)

### 4.13 UnstableSpellbook (`unstablespellbook`)
- **Level cap**: 10. **chargeCap** = `floor(level*0.6) + 2` (2 at +0, 8 at +10)
- **Scroll index**: on creation, shuffles ALL scroll types (weighted by `Generator.Category.SCROLL.defaultProbsTotal`) into an ordered `scrolls` list, excluding `ScrollOfTransmutation`. As the book levels up, the list shrinks from the front: `while scrolls.size() > (levelCap-1-level): remove(0)` — i.e., only `levelCap-1-level` scroll types remain "empowerable" at any level (0 remain at level 9+)
- **Active: "Read" (AC_READ)** — costs 1 charge:
  - Rolls a random `Scroll` via `Generator.randomUsingDefaults` (never Transmutation; halved frequency for Identify/RemoveCurse/MagicMapping — re-rolled 50% of the time)
  - If the rolled scroll's class is in the remaining `scrolls` list AND charge remains after the first deduction: offers a choice — read the rolled scroll normally, OR spend a 2nd charge to read its **Exotic** variant instead (`ExoticScroll.regToExo` mapping)
  - `artifactProc` triggers for AOE-effect scrolls: Lullaby/RemoveCurse/Terror affect all FOV-visible mobs; Rage affects ALL mobs on the level regardless of visibility
- **"Add" (AC_ADD)** — feed an identified `Scroll` matching one of the first 2 entries in `scrolls`: removes it from `scrolls`, costs the player 2 turns, then `upgrade()`s the book (each scroll fed = +1 level, raising `chargeCap`)
- **Passive recharge** (`bookRecharge`): `chargeGain = 1/(120 - (chargeCap-charge)*5) * RingOfEnergy.artifactChargeMultiplier`
- **ExploitHandler**: a safety buff that force-completes a pending "empowered read" choice if the player quits mid-prompt (prevents save-scumming the exotic-scroll choice)
- **Cursed**: no read/add actions

---

## 5. Common cross-artifact patterns

- **RingOfEnergy.artifactChargeMultiplier(target)** = `1.175^getBuffedBonus(target, Energy)`, multiplies essentially ALL passive artifact recharge rates (Cloak, Tome, Chains, Armband, Sandals, Key, Talisman, Hourglass, Spellbook, Toolkit, Horn, Rose)
- **`Regeneration.regenOn()` gate**: most passive recharges only tick while normal HP regen is active (i.e., not during certain debuffs/states)
- **Cursed artifacts** generally: lose their active ability entirely, and many have a negative passive side-effect (gold loss, hostile spawn, turn loss, debuff chance) instead of charging
- **Trinity / Well of Transmutation**: artifacts implement `resetForTrinity(visibleLevel)` to reset internal state when swapped for another artifact at the same visible (0-10) power level; `transferUpgrade(transferLvl)` converts a visible level into the artifact's actual internal level scale (`round(transferLvl*levelCap/10)`)
