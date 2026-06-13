# SPD Potions Spec

Source: `core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/potions/`

## 1. Base mechanics (`Potion.java`)

- `value()` = `30 * quantity` gold (unidentified). `energyVal()` = `6 * quantity`.
- `TIME_TO_DRINK = 1f` turn to drink.
- Each potion has a per-run random `color` (12 colors: crimson, amber, golden, jade, turquoise, azure, indigo, magenta, bistre, charcoal, silver, ivory) assigned via `ItemStatusHandler` — scrambled per seed/run, identical mechanism for scrolls.
- Identification: drinking/throwing-with-visible-effect calls `identify()` → `setKnown()`. Once any potion of a type is known, all stacks show true name/sprite.
- `anonymous` potions (spawned for effect only, e.g. unstable brew payloads): always "known", don't affect global ID state, sprite replaced with placeholder if base type unknown.
- **Talent trigger**: on drink/throw, if `Random.Float() < talentChance` (default 1.0), calls `Talent.onPotionUsed(user, pos, talentFactor)` (default `talentFactor=1`). `PotionOfStrength`, `PotionOfExperience`, `PotionOfDivineInspiration`, `PotionOfMastery` use `talentFactor=2`.
- **Throw vs drink classification**:
  - `mustThrowPots` (drinking prompts "are you sure?" harmful warning, default action = THROW): `PotionOfToxicGas`, `PotionOfLiquidFlame`, `PotionOfParalyticGas`, `PotionOfFrost`; exotic: `PotionOfCorrosiveGas`, `PotionOfSnapFreeze`, `PotionOfShroudingFog`, `PotionOfStormClouds`. All Brews except `UnstableBrew` are also must-throw (hardcoded in `Brew`).
  - `canThrowPots` (both useful drunk or thrown, default action = CHOOSE prompt): `PotionOfPurity`, `PotionOfLevitation`; exotic `PotionOfCleansing`; elixir `ElixirOfHoneyedHealing`.
  - Everything else: default action = DRINK; throwing prompts "are you sure you want to waste this beneficial potion?".
- `shatter(cell)`: plays splash VFX + "shatter" message/sound if cell in hero FOV; subclasses override to spawn blobs/effects. `onThrow`: presses cell (triggers traps) unless `AquaBrew`/`PotionOfStormClouds` (these must not disarm traps so they can interact with them specially); calls `shatter`.
- `splash()`: clears `Fire` blob at cell; if char there is an ALLY, removes `Burning`/`Ooze` debuffs (cleansing rain-like effect from any potion splash).

---

## 2. Standard Potions (12)

All standard potions: `value()=30*qty` unless noted; `energyVal()=6*qty` unless noted.

| Potion | Drink Effect | Throw/Shatter Effect | Notes |
|---|---|---|---|
| **PotionOfStrength** | `STR += 1`. Identifies on use. `unique=true` (handled specially — typically limited stock). `talentFactor=2`. | (drink-only; throwing prompts warning) | `value()=50*qty`, `energyVal()=10*qty` once known. |
| **PotionOfHealing** | `cure()` removes Poison, Cripple, Weakness, Vulnerable, Bleeding, Blindness, Drowsy, Slow, Vertigo. Then `Healing` buff: `setHeal(amount = 0.8*HT + 14, percentPerTick=0.25, flatPerTick=0)`. Heals 30 HP at HT=20, scales to equal full HT around character level ~11 (since HT grows ~5/level). `applyVialEffect()` integrates with Vial of Blood artifact (delays/limits burst healing). Under `NO_HEALING` challenge: instead inflicts `Poison.set(4 + lvl/2)` (`pharmacophobiaProc`) — ~40% max HP poison damage. | n/a (drink-only) | `bones=true` (can drop from hero remains). |
| **PotionOfMindVision** | `MindVision` buff for `DURATION=20` turns (reveals all mobs on level + grants vision through walls near them via `Dungeon.observe()`). | n/a | |
| **PotionOfFrost** | n/a (must-throw) | On shatter: seeds `Freezing` blob (volume 10) in all 9 cells (self + 8 neighbours) that aren't solid. Identifies on shatter if in FOV. | |
| **PotionOfLiquidFlame** | n/a (must-throw) | Seeds `Fire` blob (volume 2) in all 9 cells (self+neighbours) not solid. Plays SHATTER + BURNING sound. | |
| **PotionOfToxicGas** | n/a (must-throw) | Seeds `ToxicGas` blob, volume 1000, at the single target cell only. | |
| **PotionOfHaste** | `Haste` buff for `DURATION=20` turns (speed boost + stamina-ish). | n/a | `value()=40*qty`. |
| **PotionOfInvisibility** | `Invisibility` buff for `DURATION=20` turns. Plays MELD sound. | n/a | `value()=40*qty`. |
| **PotionOfLevitation** | `Levitation` buff for `DURATION=20` turns (fly over chasms/traps/water). | Seeds `ConfusionGas` blob, volume 1000, at target cell only. | `value()=40*qty`. Drink OR throw both useful (`canThrowPots`). |
| **PotionOfParalyticGas** | n/a (must-throw) | Seeds `ParalyticGas` blob, volume 1000, at target cell only. | `value()=40*qty`. |
| **PotionOfPurity** | `BlobImmunity` buff for `DURATION=20` turns (immune to gas/blob effects). Identifies on drink. | Clears ALL blobs that `BlobImmunity` grants immunity to, within distance 3 (`PathFinder.buildDistanceMap`, non-solid cells) of the shatter point. Bursts "DISCOVER" speck FX on each affected visible cell. | `value()=40*qty`. Drink OR throw both useful. |
| **PotionOfExperience** | `hero.earnExp(hero.maxExp(), ...)` — grants exactly enough XP to level up once. Yellow flare FX. `talentFactor=2`. | n/a | `value()=50*qty`, `energyVal()=10*qty`. `bones=true`. |

### Seed → Potion Recipe (`Potion.SeedToPotion`, 3-ingredient recipe, free)
Requires **3 plant seeds** (any combination from the table below, ≥1 each, must total 3 items). Cost = 0.

| Seed | → Potion |
|---|---|
| Blindweed.Seed | PotionOfInvisibility |
| Mageroyal.Seed | PotionOfPurity |
| Earthroot.Seed | PotionOfParalyticGas |
| Fadeleaf.Seed | PotionOfMindVision |
| Firebloom.Seed | PotionOfLiquidFlame |
| Icecap.Seed | PotionOfFrost |
| Rotberry.Seed | PotionOfStrength |
| Sorrowmoss.Seed | PotionOfToxicGas |
| Starflower.Seed | PotionOfExperience |
| Stormvine.Seed | PotionOfLevitation |
| Sungrass.Seed | PotionOfHealing |
| Swiftthistle.Seed | PotionOfHaste |

Logic:
- If 2 distinct seed types used: 25% (`Random.Int(4)==0`) chance to instead produce a fully **random** potion (`Generator.randomUsingDefaults(POTION)`).
- If 3 distinct seed types used: 50% (`Random.Int(2)==0`) chance for random potion.
- Otherwise: result type = the mapping of a randomly-chosen one of the 3 input seeds.
- If only 1 seed type used (all 3 same), the resulting potion is auto-identified.
- Reroll loop: if result is `PotionOfHealing`, reroll with probability `Random.Int(10) < Dungeon.LimitedDrops.COOKING_HP.count` (anti-farming — healing potions get progressively rarer from this recipe the more you've made). If `PotionOfHealing` is the final result, increments `COOKING_HP.count`.

---

## 3. Exotic Potions (alchemy-only "inverse" potions, `items/potions/exotic/`)

Each exotic potion corresponds 1:1 to a standard potion via `ExoticPotion.regToExo` / `exoToReg` maps. Exotic potions:
- Share identification state with their regular counterpart (`isKnown()`/`setKnown()` delegate to the regular potion's class).
- Sprite = regular potion's sprite image **+16** (one row down in the spritesheet), same color label.
- `value()` = regular counterpart's `value()` **+ 20** gold, times quantity.
- `energyVal()` = regular counterpart's `energyVal()` **+ 4**, times quantity.

| Regular Potion | Exotic Potion | Effect |
|---|---|---|
| PotionOfStrength | **PotionOfMastery** | Drink: opens item-select prompt. Targets one Weapon (non-SpiritBow) or Armor not yet boosted; sets `masteryPotionBonus = true` (reduces STR requirement by 2). One-time per item. `unique=true`, `talentFactor=2`. If the only copy and unidentified, identifies on use; cancel-confirmation flow via `WndOptions` warning if backing out. |
| PotionOfHealing | **PotionOfShielding** | Drink: `Barrier` buff, `setShield(amount = 0.6*HT + 10)` — roughly 75% of a Healing potion's heal value, as a damage shield instead. Under `NO_HEALING` challenge: triggers `pharmacophobiaProc` (poison) instead. |
| PotionOfMindVision | **PotionOfMagicalSight** | Drink: `MagicalSight` buff for `DURATION=50` turns (see-through-walls in 12-tile radius per description; calls `Dungeon.observe()`). |
| PotionOfFrost | **PotionOfSnapFreeze** | Must-throw. Shatter: in all 9 cells (self+8 neighbours, non-solid), instantly applies `Freezing.affect(cell)` AND if a `Char` is present, `Roots` buff for `DURATION*2 = 10` turns (rooted). Faster/stronger than regular Frost (instant freeze vs. gradual). |
| PotionOfLiquidFlame | **PotionOfDragonsBreath** | Drink triggers a **cone-targeted breath attack** instead of normal drinking (cell-selector UI). Cone: 60°, max range 6 (`ConeAOE` with `STOP_SOLID|STOP_TARGET|IGNORE_SOFT_SOLID`). All chars in the cone: `Burning.reignite()` + `Cripple` for 5 turns. Cells: doors knocked open; flammable cells ignite with `Fire` blob (volume 5); cells adjacent to caster only ignite if flammable. Also propagates fire to neighbouring flammable cells further from source. Identified-by-use flow with confirm/cancel `WndOptions`. |
| PotionOfToxicGas | **PotionOfCorrosiveGas** | Must-throw. Shatter: seeds `CorrosiveGas` blob in the 8 neighbour cells at volume 25 each (non-solid), plus center cell gets `25 + 25*(num solid neighbours)`. `setStrength(2 + Dungeon.scalingDepth()/5)` — corrosion strength scales with depth. Spreads faster, deadlier, shorter-lived than toxic gas. |
| PotionOfHaste | **PotionOfStamina** | Drink: `Stamina` buff for `DURATION=100` turns — long-lasting movement-speed/stamina-regen boost (weaker than Haste but much longer). |
| PotionOfInvisibility | **PotionOfShroudingFog** | Must-throw. Shatter: seeds `SmokeScreen` blob in 8 neighbours at volume 180 each (non-solid), center gets `180 + 180*(solid neighbour count)`. Blocks enemy vision over wide area. |
| PotionOfLevitation | **PotionOfStormClouds** | Must-throw. Shatter: seeds `StormCloud` blob in 8 neighbours at volume 120 each, center gets `120 + 120*(solid neighbours)`. Per description: converts terrain to water, damages fiery enemies, douses fire, breaks traps. Special-cased in `Potion.onThrow` (doesn't press/trigger the target cell, like AquaBrew). |
| PotionOfParalyticGas | **PotionOfEarthenArmor** | Drink: `Barkskin.conditionallyAppend(hero, amount=2 + lvl/3, cap=50)` — temporary natural armor bonus instead of paralysis. |
| PotionOfPurity | **PotionOfCleansing** | Drink: `cleanse(hero)` — removes all NEGATIVE buffs (except `AllyBuff`/`LostInventory`), satisfies Hunger fully (`Hunger.STARVING`), applies `Cleanse` buff (immunity-style icon) for `DURATION=5` turns. Yellow-pink Flare FX. Throwable (`canThrowPots`): if target cell has a `Char`, applies same cleanse to them instead of the area-purity effect; otherwise behaves like normal shatter. |
| PotionOfExperience | **PotionOfDivineInspiration** | Drink: custom flow (doesn't spend time immediately). Opens a 4-option `WndOptions` letting the player pick a talent **tier (1-4)** to receive **2 bonus talent points** in. Each tier usable only once per run, tracked via `DivineInspirationTracker` buff (`boostedTiers[1..4]`, persists through revive). If all 4 tiers already boosted, logs "no more points" and aborts (no time spent, item not consumed). On selection: plays DRINK + 2x delayed LEVELUP sounds, yellow Flare, shows level-up stars, spends 1 turn. `talentFactor=2`. |

---

## 4. Brews (`items/potions/brews/`)

All `Brew` subclasses:
- `isKnown()` always `true` (never need ID).
- Default action = THROW; drinking action removed from `actions()` (except `UnstableBrew`).
- `value() = 60 * quantity` (gold), `energyVal() = 12 * quantity`, unless overridden.
- Throwing opens a cell-selector (`GameScene.selectCell(thrower)`).

| Brew | Shatter Effect | Recipe (input → output, cost) |
|---|---|---|
| **AquaBrew** | Spawns a `GeyserTrap` at target cell and immediately `activate()`s it (forceful water burst: damages fiery enemies, spreads water, disables traps, douses fire, knockback). If thrown from a distance, computes knockback direction away from thrower via `Ballistica`. Special-cased in `Potion.onThrow` — doesn't press the target cell (lets the geyser interact with traps itself). `value()=60*(qty/8)`, `energyVal()=12*(qty/8)` (scaled because output qty=8). | `PotionOfStormClouds` x1 → `AquaBrew` x**8**, cost 8 |
| **BlizzardBrew** | Splash + SHATTER/GAS sound. Seeds `Blizzard` blob: 8 neighbours @ volume 120 each (non-solid), center = `120 + 120*solidNeighbours`. | `PotionOfFrost` x1 → `BlizzardBrew` x1, cost 8 |
| **CausticBrew** | Splash + SHATTER sound. `PathFinder.buildDistanceMap` radius 3 (non-solid); every reachable cell gets a black `Splash` FX and any `Char` there gets `Ooze` debuff set to `Ooze.DURATION=20`. | `PotionOfToxicGas` x1 + `GooBlob` x1 → `CausticBrew` x1, cost 1. (Also calls `Catalog.countUse(GooBlob.class)`.) |
| **InfernalBrew** | Splash + SHATTER/GAS sound. Seeds `Inferno` blob: 8 neighbours @ volume 120 each, center = `120 + 120*solidNeighbours`. | `PotionOfLiquidFlame` x1 → `InfernalBrew` x1, cost 12 |
| **ShockingBrew** | Splash + SHATTER/LIGHTNING sound. `PathFinder.buildDistanceMap` radius 3 (non-solid); seeds `Electricity` blob volume 20 at every reachable cell. | `PotionOfParalyticGas` x1 → `ShockingBrew` x1, cost 10 |
| **UnstableBrew** | **Drink** (re-enabled, default action = CHOOSE): rolls a random potion via weighted `potionChances` table (below), `anonymize()`s it, applies its **drink** effect. Rerolls if the rolled potion is in `mustThrowPots` (ensures always-beneficial on drink). Under `NO_HEALING` challenge, `PotionOfHealing` weight temporarily set to 0 then restored. **Throw**: rolls from the same table but rerolls until the potion is in `mustThrowPots` OR `canThrowPots` (ensures always-harmful/throwable on throw), then `shatter()`s it. `isKnown()` always true. `value()=40*qty` (cheaper), `energyVal()=8*qty`. | Recipe: any 1 **Plant.Seed** + any 1 **regular or exotic Potion** (one of each, from `ExoticPotion.regToExo`'s keys/values) → `UnstableBrew` x1, cost 1. |

### UnstableBrew potion weight table (`Random.chances`)
| Potion | Weight |
|---|---|
| PotionOfHealing | 3 |
| PotionOfMindVision | 2 |
| PotionOfFrost | 2 |
| PotionOfLiquidFlame | 2 |
| PotionOfToxicGas | 2 |
| PotionOfHaste | 2 |
| PotionOfInvisibility | 2 |
| PotionOfLevitation | 2 |
| PotionOfParalyticGas | 2 |
| PotionOfPurity | 2 |
| PotionOfExperience | 1 |

(Total weight 20; PotionOfStrength is NOT in the table.)

---

## 5. Elixirs (`items/potions/elixirs/`)

All `Elixir` subclasses:
- `isKnown()` always `true`.
- `value() = 60 * quantity`, `energyVal() = 12 * quantity` (default, some override).
- Abstract `apply(Hero)` — drink-only by default except `ElixirOfHoneyedHealing` (throwable).

| Elixir | Effect | Recipe (input → output, cost) |
|---|---|---|
| **ElixirOfAquaticRejuvenation** | Drink: applies `AquaHealing` buff, `set(amount = round(HT * 1.5))`. While standing in water (and not flying) and below max HP, heals `gate(1, HT/50, left)` HP/turn (rounded probabilistically for fractional amounts), paused outside water or at full HP. Under `NO_HEALING`: `pharmacophobiaProc` instead. | `PotionOfHealing` x1 + `GooBlob` x1 → x1, cost 6. (`Catalog.countUse(GooBlob)`.) |
| **ElixirOfArcaneArmor** | Drink: `ArcaneArmor` buff, `set(amount = 5 + lvl/2, cap=80)` — magic damage resistance. | `PotionOfEarthenArmor` x1 + `GooBlob` x1 → x1, cost 8. (`Catalog.countUse(GooBlob)`.) |
| **ElixirOfDragonsBlood** | Drink: `FireImbue` buff for `DURATION=50` turns (immune to fire, melee attacks ignite enemies). Plays BURNING sound + flame particle burst. | `PotionOfDragonsBreath` x1 → x1, cost 10 |
| **ElixirOfFeatherFall** | Drink: `Buff.append(FeatherBuff, DURATION=50)` — survive chasm falls without damage while active; `processFall()` consumes -10 duration (extends effective uses) each fall and detaches when cooldown depleted. JET particle burst. `talentChance = 1/OUT_QUANTITY` (=1, so always triggers talent since outQuantity=1). | `PotionOfLevitation` x1 → x1, cost 10 |
| **ElixirOfHoneyedHealing** | Drink: `PotionOfHealing.cure()` + `PotionOfHealing.heal()` (full healing-potion effect) + satisfies `Hunger.HUNGRY/2` + `Talent.onFoodEaten`. **Throwable** (`canThrowPots`): on shatter, any `Char` at target cell gets `cure()`+`heal()`; if target is a hostile `Bee`, it becomes an `ALLY` (pacification via honey). Cheaper: `value()=40*qty`, `energyVal()=8` flat. | `PotionOfHealing` x1 + `Honeypot.ShatteredPot` x1 → x1, cost 2 |
| **ElixirOfIcyTouch** | Drink: `FrostImbue` buff for `DURATION=50` turns (immune to cold, melee attacks chill/freeze enemies). Snow particle burst. | `PotionOfSnapFreeze` x1 → x1, cost 6 |
| **ElixirOfMight** | Drink: `STR += 1` (permanent, like Strength potion) + `HTBoost` buff `.reset()` → grants `left=5` "charges". `HTBoost.boost()` = `round(left * boost(15 + 5*lvl) / 5)` where `boost(HT) = round(4 + HT/20)`. Temporary max-HP increase that decays by 1 charge per level-up (`onLevelUp()`, detaches at 0). `hero.updateHT(true)` applied immediately. `unique=true`, `talentFactor=2`. | `PotionOfStrength` x1 → x1, cost 16 |
| **ElixirOfToxicEssence** | Drink: `ToxicImbue` buff for `DURATION=50` turns (spreads toxic gas while moving; immune to toxic gas/poison for slightly longer than duration). Poison particle splash. | `PotionOfCorrosiveGas` x1 → x1, cost 8 |

---

## 6. Waterskin (`items/Waterskin.java`)

- `unique=true`, not upgradable, always identified.
- `MAX_VOLUME = 20` "drops" of dew.
- `collectDew(Dewdrop dew)`: adds `dew.quantity` to volume (capped at 20, logs "full" message when capped).
- `fill()`: sets volume to max directly (e.g. from a fountain/source).
- `empty()`: resets volume to 0.
- **Drink action** (only available if `volume > 0`):
  - Each "drop" = 5% of hero's max HP healing.
  - `dropsNeeded = missingHealthPercent / 0.05`.
  - If Vial of Blood's `delayBurstHealing()` is active and `dropsNeeded > 1.01`, divides by `VialOfBlood.totalHealMultiplier()` (avoids over-consuming dew when burst healing is throttled).
  - Additionally, if hero has `Talent.SHIELDING_DEW`: computes `maxShield = round(HT * 0.2 * talentPoints)`, current shield from `Barrier` buff; if shield is below max, adds `missingShieldPercent * 0.2 * talentPoints / 0.05` extra drops needed (so the waterskin also tops up a damage shield).
  - `dropsToConsume = ceil(dropsNeeded - 0.01)`, clamped to `[1, volume]`.
  - Calls `Dewdrop.consumeDew(dropsToConsume, hero, true)` — applies the actual heal/shield; on success, decrements `volume`, logs catalog use, spends `TIME_TO_DRINK=1` turn, plays DRINK sound.
  - If `volume == 0`, logs "empty" warning instead.
- `status()` displays `"volume/20"`.

---

## 7. Alchemy System Overview

### Recipe.java — recipe categories
Recipes are matched by **ingredient count** via `Recipe.findRecipes(ingredients)`:

- **variableRecipes** (any count): currently empty.
- **oneIngredientRecipes** (1 item): `Scroll.ScrollToStone`, `ExoticPotion.PotionToExotic`, `ExoticScroll.ScrollToExotic`, `ArcaneResin.Recipe`, `LiquidMetal.Recipe`, `BlizzardBrew.Recipe`, `InfernalBrew.Recipe`, `AquaBrew.Recipe`, `ShockingBrew.Recipe`, `ElixirOfDragonsBlood.Recipe`, `ElixirOfIcyTouch.Recipe`, `ElixirOfToxicEssence.Recipe`, `ElixirOfMight.Recipe`, `ElixirOfFeatherFall.Recipe`, `MagicalInfusion.Recipe`, `BeaconOfReturning.Recipe`, `PhaseShift.Recipe`, `Recycle.Recipe`, `TelekineticGrab.Recipe`, `SummonElemental.Recipe`, `StewedMeat.oneMeat`, `TrinketCatalyst.Recipe`, `Trinket.UpgradeTrinket`.
- **twoIngredientRecipes** (2 items): `Blandfruit.CookFruit`, `Bomb.EnhanceBomb`, `UnstableBrew.Recipe`, `CausticBrew.Recipe`, `ElixirOfArcaneArmor.Recipe`, `ElixirOfAquaticRejuvenation.Recipe`, `ElixirOfHoneyedHealing.Recipe`, `UnstableSpell.Recipe`, `Alchemize.Recipe`, `CurseInfusion.Recipe`, `ReclaimTrap.Recipe`, `WildEnergy.Recipe`, `StewedMeat.twoMeat`.
- **threeIngredientRecipes** (3 items): `Potion.SeedToPotion`, `StewedMeat.threeMeat`, `MeatPie.Recipe`.

### Recipe.SimpleRecipe
Base class for fixed input→output recipes:
- Declares `inputs[]` (item classes), `inQuantity[]`, `cost` (energy), `output` class, `outQuantity`.
- `testIngredients`: all ingredients must be `isIdentified()`, and supplied quantities must meet/exceed `inQuantity` per input class.
- `brew()`: consumes the exact required quantities from ingredients, returns `sampleOutput()`.
- `sampleOutput()`: instantiates `output` with `outQuantity` (deterministic for SimpleRecipe).

### `usableInRecipe(item)`
- Equipable items: only allowed if `cursedKnown && !cursed` AND it's an upgradable `MissileWeapon`.
- Wands: allowed if `cursedKnown && !cursed`.
- Everything else: allowed if `!cursed` (can be unidentified).

### Alchemize spell (`items/spells/Alchemize.java`)
- Not a potion — a consumable **Spell** crafted via 2-ingredient recipe: 1 `Plant.Seed` + 1 `Runestone` → 8x `Alchemize`, cost 2.
- `value() = 20*(qty/8)`, `energyVal() = 4*(qty/8)`, `talentChance = 1/8`.
- On cast: opens item-select window (`WndAlchemizeItem`) for any sellable or energy-convertible item; lets the player instantly **sell** (gold) or **energize** (convert to wand charge energy) that item without visiting a shop/well, consuming 1 Alchemize charge per use.

### AlchemyPot / AlchemistsToolkit (`items/artifacts/AlchemistsToolkit.java`)
- The "Alchemy Pot" UI is `AlchemyScene`, launched via the **Alchemist's Toolkit** artifact (`AC_BREW` default action). The artifact has a charge system (`levelCap=10`, `charge`/`partialCharge`) and an `AC_ENERGIZE` action (consumes `RingOfEnergy`-style wand energy to refill charge). Players select 1-3 ingredient items in `AlchemyScene`, which calls `Recipe.findRecipes()` to surface valid recipes and execute `brew()`.

---

## 8. Cross-references / Buff durations used by potions

| Buff | Duration | Used by |
|---|---|---|
| `MindVision` | 20 | PotionOfMindVision |
| `Haste` | 20 | PotionOfHaste |
| `Invisibility` | 20 | PotionOfInvisibility |
| `Levitation` | 20 | PotionOfLevitation |
| `BlobImmunity` | 20 | PotionOfPurity |
| `MagicalSight` | 50 | PotionOfMagicalSight (exotic) |
| `Stamina` | 100 | PotionOfStamina (exotic) |
| `Cleanse` | 5 | PotionOfCleansing (exotic) |
| `Roots` (x2 = 10) | 5 (base) | PotionOfSnapFreeze (exotic) |
| `Freezing` blob | 10 volume | PotionOfFrost, PotionOfSnapFreeze |
| `FireImbue` | 50 | ElixirOfDragonsBlood |
| `FrostImbue` | 50 | ElixirOfIcyTouch |
| `ToxicImbue` | 50 | ElixirOfToxicEssence |
| `Ooze` | 20 | CausticBrew |
| `FeatherBuff` | 50 (consumed -10/fall) | ElixirOfFeatherFall |
| `Cripple` (from Dragon's Breath) | 5 | PotionOfDragonsBreath (exotic) |
