# SPD Spec: Seeds/Plants, Food, Trinkets, Misc/Quest Items

Sources:
- `core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/plants/`
- `core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/food/`
- `core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/trinkets/`
- `core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/{Amulet,Ankh,Dewdrop,EnergyCrystal,Honeypot,BrokenSeal}.java`
- `core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/quest/`

---

## 1. SEEDS & PLANTS

### 1.1 Plant.java base mechanics

- Each `Plant` occupies a tile (`pos`); created via `Seed.couch()` when a seed is planted/thrown onto valid ground (not pit, alchemy tile, trap, and not under `NO_HERBALISM` challenge).
- `trigger()` — called when a `Char` steps on the plant's tile:
  - Interrupts Hero if Hero stepped on it.
  - If stepper is in hero FOV and Hero has `NATURES_AID` talent: applies `Barkskin` for 2 turns, amount = `1 + 2*pointsInTalent(NATURES_AID)` (so 3 or 5 turns of Barkskin armor at talent points 1/2).
  - Calls `wither()` then `activate(ch)`.
  - Records Bestiary "seen"/encounter for the plant class.
- `wither()` — removes plant from level (`Dungeon.level.uproot`); bursts leaf particles if in FOV.
  - Seed-preservation chance: if a `WandOfRegrowth.Lotus` is in range, `seedChance = lotus.seedPreservation()`. If `Random.Float() < seedChance` and `seedClass != null && seedClass != Rotberry.Seed.class`, drops one seed of `seedClass` on the tile.
  - **Rotberry overrides `wither()`**: always drops its seed regardless of Lotus (no Lotus benefit either way), and seed is `unique = true`.
- `activate(Char ch)` — abstract; per-plant trap effect (see table below). `ch` may be `null` if no char on tile.
- Warden subclass hooks: many plants give the Warden subclass an alternate/bonus buff when the Warden steps on them (see table).

### 1.2 Plant.Seed base mechanics (`Plant.Seed extends Item`)

- `stackable = true`; `defaultAction = AC_THROW`; adds action `AC_PLANT`.
- **Throwing a seed** (`onThrow`): if target cell is `Terrain.ALCHEMY`, a pit, has a trap, or `NO_HERBALISM` challenge active → behaves as normal throw (drops item). Otherwise: `Dungeon.level.plant(this, cell)` — the seed is consumed and a `Plant` is grown on that tile. If Hero is Warden, all 8 neighboring `EMPTY`/`EMPTY_DECO`/`EMBERS`/`GRASS` tiles become `FURROWED_GRASS` (decorative, leaf particle burst).
- **AC_PLANT action**: same as throwing onto the hero's own tile; costs `TIME_TO_PLANT = 1` turn, plays plant sound if visible.
- `isUpgradable() = false`; `isIdentified() = true` always (seeds are never unidentified).
- Base seed `value() = 10 * quantity`, `energyVal() = 2 * quantity` (used for Alchemy "Strength of 1000" / fuel costs).
- `Seed.PlaceHolder` — generic placeholder image (`SEED_HOLDER`), `isSimilar` matches any `Plant.Seed`.

### 1.3 Per-plant table — trap (stepped-on) effects

| Plant | Image idx | Trap Effect on `activate(ch)` |
|---|---|---|
| **Sungrass** | 3 | Heals over time: applies `Sungrass.Health` buff with `level = ch.HT` (boosts existing level if present). Heals 1 HP every ~`150/(40+HT)` turns (full heal ~50/93/111/120 turns at HT for lvl 1/10/20/30 hero). Warden: instead gets `Healing` buff for full HT over 1 turn (instant heal). Emits light shaft particles. |
| **Fadeleaf** | 10 | Hero: `curAction = null`; if Warden AND interfloor teleport allowed → returns to floor `depth-1` via `InterlevelScene` (RETURN mode); else `ScrollOfTeleportation.teleportChar`. Mob (non-`IMMOVABLE`): gets `HazardAssistTracker` buff then is teleported. Light particle burst. |
| **Icecap** | 4 | Freezes all 9 cells in 3x3 (`NEIGHBOURS9`) that are non-solid via `Freezing.affect`. Any `Mob` in those cells gets `HazardAssistTracker`. Warden (if char): gets `FrostImbue` for `0.3 * DURATION`. |
| **Firebloom** | 1 | Seeds a `Fire` blob with strength 2 at the tile (`Blob.seed(pos, 2, Fire.class)`). Mob on tile gets `HazardAssistTracker`. Warden: gets `FireImbue` for `0.3 * DURATION`. Flame particle burst. |
| **Sorrowmoss** | 6 | Applies `Poison` for `5 + round(2*scalingDepth/3)` turns to `ch`. Mob gets `HazardAssistTracker`. Warden: gets `ToxicImbue` for `0.3 * DURATION`. Poison particle splash. |
| **Swiftthistle** | 2 | Applies/resets `Swiftthistle.TimeBubble` buff (freezes time for `6+1` turns — "Time Freeze" effect: all mobs paralysed visually, pending plant/trap triggers on cells delayed until bubble ends). Warden: also gets `Haste` for 1 turn. |
| **Blindweed** | 11 | `ch != null`: Warden gets `Invisibility` for `DURATION/2`. Otherwise: `Blindness` + `Cripple` (both full `DURATION`). If `ch` is Mob: gets `HazardAssistTracker`; if `HUNTING` → switches to `WANDERING` and `beckon`s to a random destination. Light speck burst. |
| **Stormvine** | 5 | Warden: `Levitation` for `DURATION/2`. Otherwise: Mob gets `HazardAssistTracker`; `ch` gets `Vertigo` for full `DURATION` (confusion-like random movement). |
| **Earthroot** | 8 | Warden: `Barkskin.conditionallyAppend(hero, hero.lvl+5, 5)` (5 turns of armor = lvl+5). Otherwise: applies `Earthroot.Armor` buff, `level(ch.HT)` — raises armor buff level to `ch.HT` if currently lower. `Earthroot.Armor.absorb(damage)`: blocks up to `(scalingDepth+5)/2` damage per hit until depleted. Earth particles + screen shake. |
| **Mageroyal** | 7 | `PotionOfHealing.cure(ch)` — cures all negative debuffs (poison, burning, etc., NOT a heal). Hero: logs "refreshed". Warden: also gets `BlobImmunity` for `DURATION/2`. |
| **Starflower** | 9 | Applies `Bless` for full `DURATION` (immunity-ish buff that prevents next debuff/lucky escape). Yellow flare VFX if in FOV. Warden: also gets `Recharging` for full `DURATION` + charge spell VFX. |
| **Rotberry** | 0 | Warden: `AdrenalineSurge` reset(1, DURATION). Otherwise: seeds a massive `ToxicGas` blob, strength 100, at the tile (huge toxic cloud). |
| **BlandfruitBush** | 12 | Drops a raw `Blandfruit` item on the tile. No seed class (`seedClass` unset) — never drops a seed; this "plant" is a fixed bush feature, not grown from a seed. |

### 1.4 Per-seed table — direct-use effects (Alchemy / cooking / drop properties)

All seeds: `isUpgradable=false`, `isIdentified=true`, default action `THROW` (or `PLANT`). Base `value=10*qty`, `energyVal=2*qty` unless overridden.

| Seed | Sprite const | value() | energyVal() | `bones` (drop on death) | unique | SeedToPotion (3-seed alchemy w/ "Strength" reagent → potion) |
|---|---|---|---|---|---|---|
| Sungrass.Seed | `SEED_SUNGRASS` | 10×qty | 2×qty | true | — | → `PotionOfHealing` |
| Fadeleaf.Seed | `SEED_FADELEAF` | 10×qty | 2×qty | — | — | → `PotionOfMindVision` |
| Icecap.Seed | `SEED_ICECAP` | 10×qty | 2×qty | — | — | → `PotionOfFrost` |
| Firebloom.Seed | `SEED_FIREBLOOM` | 10×qty | 2×qty | — | — | → `PotionOfLiquidFlame` |
| Sorrowmoss.Seed | `SEED_SORROWMOSS` | 10×qty | 2×qty | — | — | → `PotionOfToxicGas` |
| Swiftthistle.Seed | `SEED_SWIFTTHISTLE` | 10×qty | 2×qty | — | — | → `PotionOfHaste` |
| Blindweed.Seed | `SEED_BLINDWEED` | 10×qty | 2×qty | — | — | → `PotionOfInvisibility` |
| Stormvine.Seed | `SEED_STORMVINE` | 10×qty | 2×qty | — | — | → `PotionOfLevitation` |
| Earthroot.Seed | `SEED_EARTHROOT` | 10×qty | 2×qty | true | — | → `PotionOfParalyticGas` |
| Mageroyal.Seed | `SEED_MAGEROYAL` | 10×qty | 2×qty | — | — | → `PotionOfPurity` |
| Starflower.Seed | `SEED_STARFLOWER` | **30×qty** | **3×qty** | — | — | → `PotionOfExperience` |
| Rotberry.Seed | `SEED_ROTBERRY` | **30×qty** | **3×qty** | — | **true** | → `PotionOfStrength` |

**SeedToPotion alchemy recipe** (`Potion.SeedToPotion`, in `Potion.java`): combine 1 seed + 2 other reagents (3 total ingredients) — outputs a potion of the type mapped above (anonymous "name=SeedToPotion" potion until further identified). Used as the standard "convert seed to its corresponding potion" Alchemy Pot recipe.

**Cooking seed into Blandfruit** (`Blandfruit.CookFruit` recipe, see Food section): 1 raw `Blandfruit` + 1 seed (any quantity≥1 each) → cost 2 energy → cooked `Blandfruit` imbued with the potion from `SeedToPotion.types` map for that seed, named per-fruit (sunfruit/rotfruit/earthfruit/blindfruit/firefruit/icefruit/fadefruit/sorrowfruit/stormfruit/dreamfruit/starfruit/swiftfruit).

**Berry seed drop** (`Berry.SeedCounter`): every 2nd Berry eaten drops a random seed (`Generator.Category.SEED`) at hero's position.

---

## 2. FOOD

### 2.1 Food.java base mechanics

- `TIME_TO_EAT = 3f` turns (action `AC_EAT`, default action).
- `energy` field = hunger restored, in Hunger-buff units. Hunger constants: `HUNGRY = 300`, `STARVING = 450`.
- `eatingTime()`: normally `3f`; reduced by 2 (→ `1f`) if hero has any of: `IRON_STOMACH`, `ENERGIZING_MEAL`, `MYSTICAL_MEAL`, `INVIGORATING_MEAL`, `FOCUSED_MEAL`, `ENLIGHTENING_MEAL` talents.
- `satisfy(hero)`:
  - `foodVal = energy`; if `NO_FOOD` challenge active, `foodVal /= 3`.
  - If `HornOfPlenty.hornRecharge` buff present and cursed: `foodVal *= 0.67` (and logs "cursedhorn").
  - `Buff.affect(hero, Hunger.class).satisfy(foodVal)`.
- On eat: detaches item, counts use in Catalog, logs "eat_msg", plays eat SFX, shows FOOD spell sprite, spends `eatingTime()`, calls `Talent.onFoodEaten(hero, energy, this)`, increments `Statistics.foodEaten`.
- Base `value() = 10 * quantity`; `isUpgradable=false`, `isIdentified=true`, `stackable=true`, `bones=true` (can appear in bones-pile drops) unless overridden.

### 2.2 Per-food table

| Food | Image | `energy` (hunger restored) | `value()` | `bones` | Special effects |
|---|---|---|---|---|---|
| **Food** (Ration of Food, base class) | `RATION` | `HUNGRY` = 300 | 10×qty | true | None — baseline ration. |
| **SmallRation** | `OVERPRICED` | `HUNGRY/2` = 150 | 10×qty | (inherits true) | None. |
| **SupplyRation** | `SUPPLY_RATION` | `2*HUNGRY/3` ≈ 200 | 10×qty | **false** | `eatingTime()=0` w/ meal talents else `1f`. On eat: heals 5 HP (capped at max HT); if hero carries `CloakOfShadows`, gives it 1 direct charge + triggers `ScrollOfRecharging.charge`. |
| **MysteryMeat** | `MEAT` | `HUNGRY/2` = 150 | 5×qty | (default) | On eat, rolls `Random.Int(5)` → 4/5 chance of random negative effect: 0=`Burning.reignite`, 1=`Roots` ×2 duration, 2=`Poison.set(HT/5)`, 3=`Slow` (full duration), 4=nothing. Has `PlaceHolder` subclass matching MysteryMeat/StewedMeat/ChargrilledMeat/FrozenCarpaccio for stacking. |
| **StewedMeat** | `STEWED` | `HUNGRY/2` = 150 | 8×qty | (default) | No special eat effect — "cured" mystery meat. Crafted via `Recipe.SimpleRecipe`: 1 MysteryMeat (cost 1) → 1 StewedMeat; 2 MysteryMeat (cost 2) → 2 StewedMeat; 3 MysteryMeat (cost 2) → 3 StewedMeat. |
| **ChargrilledMeat** | `STEAK` | `HUNGRY/2` = 150 | 8×qty | (default) | No special eat effect. `cook(quantity)` static factory (produced by cooking fire / similar). |
| **FrozenCarpaccio** | `CARPACCIO` | `HUNGRY/2` = 150 | 10×qty | (default) | On eat, rolls `Random.Int(5)` → 4/5 chance of positive effect: 0=`Invisibility` (full DURATION), 1=`Barkskin.conditionallyAppend(HT/4, 1)`, 2=`PotionOfHealing.cure`, 3=heal `HT/4` HP, 4=nothing. `cook(MysteryMeat ingredient)` factory preserves quantity. |
| **PhantomMeat** | `PHANTOM_MEAT` | `STARVING` = 450 | 30×qty | (default) | On eat, **always** applies all of: `Barkskin.conditionallyAppend(HT/4, 1)`, `Invisibility` (full DURATION), heal `HT/4` HP, `PotionOfHealing.cure`. |
| **Pasty** | `PASTY` (varies by holiday — see below) | `STARVING` = 450 (or `HUNGRY` on Lunar New Year) | 20×qty | true | Holiday-dependent name/sprite/effect (see §2.3). |
| **Pasty.FishLeftover** | `FISH_LEFTOVER` | `HUNGRY/2` = 150 | 10×qty | (default) | Plain extra food item granted on Lunar New Year pasty-eating. |
| **MeatPie** | `MEAT_PIE` | `STARVING*2` = 900 | 40×qty | (default) | On eat, also applies `WellFed` buff (`reset()` — temporary stat boost buff). Crafted via `MeatPie.Recipe`: requires (Pasty OR PhantomMeat) + (plain Food ration) + (MysteryMeat/StewedMeat/ChargrilledMeat/FrozenCarpaccio), cost 6 energy, consumes 1 of each, yields 1 MeatPie. |
| **Berry** (dungeon berry) | `BERRY` | `HUNGRY/3` ≈ 100 | 5×qty | **false** | `eatingTime()=0` w/ meal talents else `1f`. Tracks `Berry.SeedCounter` (revive-persistent); every 2nd berry eaten drops a random seed at hero's feet. |
| **Blandfruit** (raw) | `BLANDFRUIT` | n/a (raw — `AC_EAT` blocked, logs "raw" warning) | 20×qty | true | Raw blandfruit cannot be eaten. Must be cooked with a seed (see §1.4) to imbue `potionAttrib`. |
| **Blandfruit** (cooked, imbued) | `BLANDFRUIT` (+ glow) | `STARVING` = 450 | 20×qty | true | `defaultAction` = potion's drink action if drinkable, else `AC_EAT`. Eating triggers `potionAttrib.apply(hero)` AND normal Food.satisfy. Throwing a cooked fruit whose potion is one of {LiquidFlame, ToxicGas, ParalyticGas, Frost, Levitation, Purity} shatters the potion effect at impact and drops `Blandfruit.Chunks`; other potion types throw normally. Named per potionAttrib: sunfruit (Healing), rotfruit (Strength), earthfruit (ParalyticGas), blindfruit (Invisibility), firefruit (LiquidFlame), icefruit (Frost), fadefruit (MindVision), sorrowfruit (ToxicGas), stormfruit (Levitation), dreamfruit (Purity), starfruit (Experience), swiftfruit (Haste). |
| **Blandfruit.Chunks** | `BLAND_CHUNKS` | `STARVING` = 450 | (inherits 20×qty) | true | Leftover item dropped when a shatterable cooked blandfruit is thrown. |

### 2.3 Pasty holiday variants (`Holiday.getCurrentHoliday()`)

| Holiday | Sprite/name | Extra effect on eat |
|---|---|---|
| NONE (default) | PASTY / "pasty" | none |
| LUNAR_NEW_YEAR | STEAMED_FISH / "fish_name" | `energy` forced to `HUNGRY` (not STARVING); drops a `FishLeftover` (HUNGRY/2) item too |
| APRIL_FOOLS | CHOC_AMULET / "amulet_name" | plays MIMIC sound, then falls through to EASTER effect |
| EASTER | EASTER_EGG / "egg_name" | `ArtifactRecharge.chargeArtifacts(hero, 2f)` + `ScrollOfRecharging.charge` |
| PRIDE | RAINBOW_POTION / "rainbow_name" | charms an adjacent non-boss enemy for 5 turns; rainbow particle burst |
| SHATTEREDPD_BIRTHDAY / PD_BIRTHDAY | SHATTERED_CAKE / VANILLA_CAKE | grants EXP = `max(2, maxExp/10)` |
| HALLOWEEN | PUMPKIN_PIE / "pie_name" | heals `max(3, HT/20)` HP |
| WINTER_HOLIDAYS | CANDY_CANE / "cane_name" | charges belongings by 0.5 (≈2 turns) + `ScrollOfRecharging.charge` |
| NEW_YEARS | SPARKLING_POTION / "sparkling_name" | shields hero for `max(5, HT/10)` via `Barrier` |

---

## 3. TRINKETS

### 3.1 Trinket.java base mechanics

- All trinkets: `levelKnown = true`, `unique = true`, `isUpgradable() = false` (cannot use Scroll of Upgrade — leveled only via `TrinketCatalyst` recipe).
- `level()` ranges 0–3 (4 tiers: base + 3 upgrades). `trinketLevel(Class)` returns hero's current trinket's `buffedLvl()`, or `-1` if hero doesn't have that trinket.
- `energyVal() = 5` (Alchemy fuel value if discarded into pot).
- `info()` appends `statsDesc()` — a per-trinket formatted description of current numeric effect.
- `Trinket.PlaceHolder` — generic placeholder, matches any `Trinket` for stacking display.
- `Trinket.UpgradeTrinket` Recipe: 1 trinket (level < 3) + cost = `upgradeEnergyCost()` → upgrades it by 1 level. Two cost progressions used across trinkets:
  - **Cheap progression**: `6 + 2*level` → total cumulative cost to reach lvl 1/2/3 = 6/14/24/36 energy.
  - **Expensive progression**: `10 + 5*level` → cumulative 10/16/31/51 energy.

### 3.2 TrinketCatalyst.java mechanics

- `TrinketCatalyst extends Item`: `unique=true`, always identified, not upgradable.
- On pickup, flashes the Alchemy Guide page if unread.
- `TrinketCatalyst.Recipe`: 1 catalyst, cost 6 energy → consumes the catalyst, opens `WndTrinket` reward window (rolls 4 random trinkets via `Generator.Category.TRINKET`, cached in `rolledTrinkets` so a re-opened save shows the same 4 options).
- `WndTrinket`: player picks 1 of 4 rolled trinkets (or a `RandomTrinket` placeholder which re-rolls fully randomly on confirm); chosen trinket is identified and crafted/added to inventory; consumes the catalyst.
- `TrinketCatalyst.RandomTrinket` — placeholder item (`SOMETHING` sprite) representing "pick a fully random trinket" option.

### 3.3 Per-trinket effect table (by level: base=lvl0 .. max=lvl3, "−1"=not owned)

| Trinket | Upgrade cost | Effect formula | Values @ lvl -1/0/1/2/3 |
|---|---|---|---|
| **RatSkull** | cheap (6/8/10/12 → cumul 6/14/24/36) | `exoticChanceMultiplier(lvl) = 2 + lvl` (multiplier to chance of "exotic" ingredient/item rolls); lvl=-1 → 1 | 1× / 2× / 3× / 4× / 5× |
| **ParchmentScrap** | expensive (10/15/20/25 → cumul 10/16/31/51... actually `10+5*lvl`) | `enchantChanceMultiplier(lvl)`: scroll-of-enchant find-chance multiplier. `curseChanceMultiplier(lvl)`: cursed-item chance multiplier | enchant: 1× / 2× / 4× / 7× / 10×.  curse: 1× / 1.5× / 2× / 1× / 0× |
| **PetrifiedSeed** | cheap | `stoneInsteadOfSeedChance(lvl)`: chance grass produces a Stone of Enchant/etc instead of a Seed. `grassLootMultiplier(lvl) = 1 + 0.25*lvl/3` extra grass loot quantity | stone%: 0/25/46/65/80%. grass loot: 1× / 1.083× / 1.167× / 1.25× |
| **ExoticCrystals** | cheap | `consumableExoticChance(lvl) = 0.125 + 0.125*lvl` — chance a consumable (potion/scroll) rolled is "exotic" variant; lvl=-1 → 0 | 0% / 12.5% / 25% / 37.5% / 50% |
| **MossyClump** | expensive | `overrideNormalLevelChance(lvl) = 0.25 + 0.25*lvl` — chance the level's "feeling" (Grass/Water) is forced rather than random. Maintains a shuffled pre-seeded queue of 2×GRASS+4×WATER feelings (seeded `Dungeon.seed+1`, reshuffled each cycle) | 0% / 25% / 50% / 75% / 100% |
| **DimensionalSundial** | cheap | Daytime (8:00-19:59 real time) enemy spawn multiplier `= 0.95 - 0.05*lvl`; nighttime (20:00-7:59) multiplier `= 1.25 + 0.25*lvl`. lvl=-1 → 1× both | day: 1×/0.95×/0.90×/0.85×/0.80×.  night: 1×/1.25×/1.50×/1.75×/2.00× |
| **ThirteenLeafClover** | cheap | `alterHeroDamageChance(lvl) = 0.25 + 0.25*lvl` — chance hero's damage roll is altered. When altered, `MAX_CHANCE=0.6` chance result = max roll, else = min roll (i.e. "reroll toward extremes", net positive for hero) | alter%: 0/25/50/75/100. Of those: 60% → max dmg, 40% → min dmg |
| **TrapMechanism** | cheap | `overrideNormalLevelChance(lvl) = 0.25+0.25*lvl` — forces level "feeling" Traps/Chasm (3×TRAPS+3×CHASM seeded queue, like MossyClump). `revealHiddenTrapChance(lvl) = 0.1+0.1*lvl` — chance to reveal hidden traps | feeling%: 0/25/50/75/100. reveal%: 0/10/20/30/40 |
| **MimicTooth** | cheap | `mimicChanceMultiplier(lvl) = 1.5+0.5*lvl` — multiplier to mimic-spawn chance from item heaps. `stealthyMimics() = true` if owned (≥lvl0) — mimics don't reveal early. `ebonyMimicChance(lvl) = 0.125+0.125*lvl` — chance a spawned mimic is the rare "ebony" variant; <0 → 0 | mimic mult: 1×/1.5×/2×/2.5×/3×. ebony%: 0/12.5/25/37.5/50 |
| **WondrousResin** | expensive | `positiveCurseEffectChance(lvl) = 0.25+0.25*lvl` — chance a "cursed" effect roll is replaced with a positive one instead. `extraCurseEffectChance(lvl) = 0.125+0.125*lvl` — chance of an *additional* curse effect bonus roll. `forcePositive` static flag used when generating bonus effects | positive%: 0/25/50/75/100. extra%: 0/12.5/25/37.5/50 |
| **EyeOfNewt** | cheap | `visionRangeMultiplier(lvl) = 0.875-0.125*lvl` — multiplier reducing hero's normal FOV radius (lvl<0→1, i.e. no reduction). `mindVisionRange(lvl) = 2+lvl` — radius of permanent passive mind-vision around hero (lvl<0→0) | FOV mult: 1×/0.875×/0.75×/0.625×/0.5×. mind-vision radius: 0/2/3/4/5 |
| **SaltCube** | cheap | `hungerGainMultiplier(lvl) = 1/(1+0.25*(lvl+1))` — multiplies hunger accumulation rate (lower = slower hunger). `healthRegenMultiplier(lvl)`: multiplies natural HP regen rate (lower = slower regen, tradeoff) | hunger mult: 1×/0.8×/0.667×/0.571×/0.5×.  regen mult: 1/0.84/0.73/0.66/0.6 |
| **VialOfBlood** | cheap | `delayBurstHealing() = true` if owned — large heals from Dewdrops/etc are spread over multiple turns instead of instant. `totalHealMultiplier(lvl) = 1+0.125*(lvl+1)` — total healing amount multiplier. `maxHealPerTurn(lvl)`: caps per-turn heal amount during the delayed heal | total heal mult: 1×/1.125×/1.25×/1.375×/1.5×.  max/turn (lvl-1 = unlimited = full maxHP): lvl0=`4+15%maxHP`, lvl1=`3+10%`, lvl2=`2+7%`, lvl3=`1+5%` |
| **ShardOfOblivion** | cheap | `passiveIDDisabled() = true` if owned (≥lvl0) — passive item identification over time is disabled. `lootChanceMultiplier(lvl) = 1 + 0.2*min(wornUnIDed, lvl+1)` where `wornUnIDed` counts currently-unidentified equipped weapon/armor/ring/misc + recent wand-use/thrown-weapon trackers (via `WandUseTracker`/`ThrownUseTracker` flavour buffs, 50-turn duration). `AC_IDENTIFY` action: instantly identifies a selected unidentified upgradable item if it's "ready" (per-item-type readiness check, or via Intuition talents at 2 points) | loot mult @ wornUnIDed capped to (lvl+1): up to 1.2×/1.4×/1.6×/1.8×/2.0× for lvl -1..3 (lvl-1 → always 1×) |
| **ChaoticCenser** | cheap | `averageTurnsUntilGas(lvl) = 300/(lvl+1)`; lvl<0 → -1 (disabled). Every ~3 turns (via `CenserGasTracker`), if a valid enemy is targeted and "left" countdown ≤0, spawns a random gas blob 2-6 tiles from hero (aimed near target) — category odds (common/uncommon/rare) scale with level: lvl0 70/25/5, lvl1 60/30/10, lvl2 50/35/15, lvl3 40/40/20. Common gases: ToxicGas(300), ConfusionGas(300), Regrowth(200, skipped if regen off). Uncommon: StormCloud(300), SmokeScreen(300), StenchGas(200). Rare: Inferno(300), Blizzard(300), CorrosiveGas(200, sets corrosion strength `2+scalingDepth/5`) | avg turns until gas: ∞(disabled)/300/150/100/75 |
| **FerretTuft** | cheap | `evasionMultiplier(lvl) = 1 + 0.125*(lvl+1)` — multiplier to hero evasion chance; lvl<0 → 1× | 1×/1.125×/1.25×/1.375×/1.5× |
| **CrackedSpyglass** | cheap | `extraLootChance(lvl) = 0.375*(lvl+1)` — chance of bonus loot drop from defeated enemies; at lvl≥2 this exceeds 100% so description switches to "extra loot guaranteed + X% chance of a 2nd extra item" framing (`stats_desc_upgraded`) | 0%/37.5%/75%/112.5%(→100%+12.5% extra)/150%(→100%+50% extra) |

---

## 4. MISC / QUEST ITEMS (`items/` root + `items/quest/`)

### 4.1 Amulet of Yendor (`Amulet.java`)

- `unique=true`, always identified, not upgradable.
- Picking it up for the first time (`Statistics.amuletObtained` flag): refunds hero's action cooldown, then (after current actions resolve) switches to `AmuletScene` with celebratory text (game-win cutscene). Sets `amuletObtained=true`, validates "Victory" and "Champion" badges, full save.
- Action `AC_END`: re-opens `AmuletScene` without text (lets player re-trigger the "end game" scene at will) — hidden if hero has the `AscensionChallenge` buff (Ascension mode disables manual ending).
- `desc()`: appends "desc_origins" normally, or "desc_ascent" if in Ascension challenge.

### 4.2 Ankh (`Ankh.java`)

- `bones=true` (can be found in bones piles); not upgradable; always identified.
- Revival item — primary mechanic lives in `Hero`/death-handling code (not shown here), Ankh's own file only governs the **blessing** mechanic:
  - Action `AC_BLESS` available if hero carries a full `Waterskin` and Ankh is not yet blessed.
  - Blessing: empties the waterskin, sets `blessed=true`, plays drink sound + light particle burst, costs 1 turn. A blessed Ankh shows `desc_blessed` text and glows white (`Glowing(0xFFFFCC)`).
  - `value() = 50 * quantity`.

### 4.3 Dewdrop (`Dewdrop.java`)

- `stackable=true`, `dropsDownHeap=true`, not upgradable, always identified. Max stack quantity capped at 1 via overridden `merge`/`quantity`.
- On pickup: if hero carries a non-full `Waterskin`, the dew is absorbed into the waterskin (`collectDew`) instead of inventory.
- Otherwise, immediately applies `consumeDew(1, hero, force)`:
  - `effect = round(HT * 0.05 * quantity)` — **1 dewdrop = 5% max HP** worth of healing/shielding (20 dewdrops = full heal).
  - `heal = min(HT-HP, effect)`.
  - If hero has `SHIELDING_DEW` talent: any leftover `effect-heal` becomes `Barrier` shielding, capped at `20% maxHP * talent points` total shield.
  - If `quantity>1` and `VialOfBlood.delayBurstHealing()` active, large heals are spread via `Healing` buff (`setHeal` + `applyVialEffect`) instead of instant.
  - `force=true` when picked up on entrance/exit stairs tiles — always consumes even if already at full HP (avoids "already full" message blocking stairway pickup).
  - If no heal/shield happens and not forced: logs "already_full", pickup fails (returns false).

### 4.4 EnergyCrystal (`EnergyCrystal.java`)

- `stackable=true`, not upgradable, always identified, **no actions** (`actions()` returns empty list — cannot be dropped/thrown/used manually).
- On pickup: directly adds `quantity` to `Dungeon.energy` (global Alchemy-pot fuel pool); shows floating "+N energy" text (cyan `0x44CCFF`), plays ITEM sound, spends `pickupDelay()`.
- Constructor `EnergyCrystal(int value)` sets `quantity = value` directly (used by Alchemy pot byproduct drops, etc.)

### 4.5 Honeypot (`Honeypot.java`)

- `stackable=true`, `defaultAction=AC_THROW`, `usesTargeting=true`; not upgradable, always identified. `value() = 30 * quantity`.
- Action `AC_SHATTER`: shatters at hero's feet — same as throwing onto self.
- `shatter(owner, pos)`: plays SHATTER sound + yellow splash (`0xffd500`) if visible; spawns a `Bee` (scaled to `Dungeon.scalingDepth()`, full HP) at `pos` or an adjacent free non-solid cell (`setPotInfo` links bee to the pot location/owner); returns a `Honeypot.ShatteredPot` item.
- `onThrow`: if target is a pit, normal throw (drops item); else shatters at the cell and drops the resulting `ShatteredPot`.
- **ShatteredPot** (`SHATTPOT` sprite, stackable, `value()=5*quantity`): an inert "broken pot" item that tracks the bee(s) spawned from it.
  - Picking it up / dropping it / throwing it updates the position info of up to `quantity` `Bee`s whose `potPos()`/`potHolderID()` match, via `setPotInfo` — i.e., bees know where "their" pot currently is (carried by hero or sitting on the ground), affecting bee AI (presumably bees return to/guard the pot).

### 4.6 BrokenSeal (`BrokenSeal.java`) — Huntress class item

- `cursedKnown=levelKnown=true`, `unique=true`, `bones=false`; `defaultAction=AC_INFO` (shows info window — tutorial purposes when used from quickslot).
- `isUpgradable() = (level()==0)` — can be upgraded exactly once via Scroll of Upgrade (equivalent to upgrading affixed armor then detaching the seal).
- Carries an optional `Armor.Glyph` (glyph affixed to it, transferable to/from armor).
- `canTransferGlyph()`: true if `RUNIC_TRANSFERENCE` talent at 2 points (any glyph), or at 1 point limited to `Armor.Glyph.common`/`uncommon` glyph classes.
- `maxShield(armTier, armLvl) = 3 + 2*armTier + pointsInTalent(IRON_WILL)` — range 5-15 depending on armor tier (1-5) and Iron Will talent.
- Action `AC_AFFIX`: opens item-selector restricted to `Armor` in backpack. `affixToArmor(armor, outgoing)`:
  - Refuses if armor's curse status unknown, or armor is cursed and the seal's current glyph isn't itself a "curse"-type glyph.
  - If armor already has a different glyph and transfer is allowed: prompts player to choose which glyph (seal's or armor's) survives the affix.
  - Otherwise: detaches seal from backpack (or removes seal from prior armor), affixes seal to the new armor, plays UNLOCK sound + operate animation.
- **WarriorShield** (`BrokenSeal.WarriorShield extends ShieldBuff`): the seal's combat ability once affixed to equipped armor.
  - `shieldUsePriority = 2`; `detachesAtZero = false`.
  - `maxShield()`: if hero class ≠ Warrior and has `IRON_WILL` talent → returns `pointsInTalent(IRON_WILL)` directly (metamorphed effect); else if armor is equipped and has this seal affixed → `seal.maxShield(armor.tier, armor.level())`; else 0.
  - `activate()`: grants `maxShield()` shield points, sets cooldown to `cooldown + COOLDOWN_START(150)` (stacks negative cooldown if activated again while on cooldown).
  - Decay: if shield > 0 and hero has had no visible enemies (and no `Combo` buff) for ≥5 turns (turn-rate scaled by `HoldFast.buffDecayFactor`), the shield decays to 0 and refunds up to 50% of remaining cooldown proportional to remaining shield%.
  - Cooldown ticks down by 1/turn (only while `Regeneration.regenOn()`).

### 4.7 Quest items (`items/quest/`)

| Item | Sprite | Stackable | Special properties |
|---|---|---|---|
| **CeremonialCandle** | `CANDLE` | yes | `unique=true`; default action THROW. Used in the Wandmaker side-quest ritual (`RitualSiteRoom`, position tracked in static `ritualPos`). Has `aflame` bundled bool; becomes lit (`aflame=true`) automatically when all 4 cells around `ritualPos` (N/E/S/W) hold a heap containing an unlit candle. When all 4 candles present & lit, they're consumed and spawn a `Elemental.NewbornFireElemental` (state=HUNTING) near `ritualPos`, with fire particle bursts + BURNING sound. Updates Wandmaker quest music on Prison level. |
| **CorpseDust** | `DUST` | no | `cursed=true, cursedKnown=true, unique=true`; **no actions at all** (cannot be dropped). On pickup: logs "chill", attaches `DustGhostSpawner` buff to hero (revive-persistent, but checks dust still held). Spawner increments `spawnPower` each turn; needs `min(49, wraiths²)` power (where `wraiths` = 1 + currently-alive `DustWraith`s) to spawn a new `DustWraith` at a random visible cell ≥`viewDistance/3` tiles away. `DustWraith` (extends `Wraith`): first hit on hero free, 2nd/3rd hits each cost -100 to `Statistics.questScores[1]`. Removing the item (`onDetach`) calls `spawner.dispel()` — detaches buff and kills all active DustWraiths, fades music back to level music. |
| **DarkGold** | `ORE` | yes | `unique=true`; always identified, not upgradable. Plain quest-currency/ore item (Dwarf King / Imp quest line — no special logic beyond base Item). |
| **DwarfToken** | `TOKEN` | yes | `unique=true`; always identified, not upgradable. Plain quest-token item, no special logic. |
| **Embers** ("elemental embers") | `EMBER` | no | `unique=true`; always identified, not upgradable. Glows red (`Glowing(0x660000, 3f)`). No other logic — carried quest item (Wandmaker quest reward material). |
| **EscapeCrystal** | `ESCAPE` | no | `unique=true`; default action `AC_USE`. Only usable when `15 < Dungeon.depth < 20`, `branch==1`, and `Dungeon.level instanceof VaultLevel` (the post-game "Amulet branch" Vault). On use: plays TELEPORT sound, strips all wand/artifact/ring charge buffs and `ClassArmor.Charger` (but not melee-charger, so Duelist keeps combo charge), calls `storeHeroBelongings`/`restoreHeroBelongings` round-trip (effectively resets HT via `updateHT(false)`), then transitions the hero back down via `InterlevelScene` (ASCEND mode) using a `BRANCH_ENTRANCE`→`BRANCH_EXIT` `LevelTransition` at the current depth/branch 0. Detaches all items from backpack after transition starts. `storeHeroBelongings`/`restoreHeroBelongings`: serialize/restore full `Belongings`, quickslot placeholders, gold, and energy into an internal `storedItems` bundle — used to "park" the hero's inventory while escaping the Vault. |
| **GooBlob** | `BLOB` | yes | not upgradable, always identified. `value() = 30*quantity`, `energyVal() = 3*quantity`. Quest material (Goo boss questline) — Alchemy fuel/sell value only, no other logic. |
| **MetalShard** ("cursed metal shard") | `SHARD` | yes | not upgradable, always identified. `value() = 50*quantity`, `energyVal() = 3*quantity`. Quest material — Alchemy fuel/sell value only, no other logic. |
| **Pickaxe** | `PICKAXE` | n/a (weapon) | `MeleeWeapon` subclass, tier=2 damage but `STRReq` = tier-3 requirement (`super.STRReq(lvl)+2`); `levelKnown=true, unique=true, bones=false`. On `MiningLevel`, `AC_DROP`/`AC_THROW` actions are removed and `keptThroughLostInventory()` always true while on a MiningLevel (can't lose it before finishing the mining sequence). Duelist ability (`duelistAbility`): single-target attack at `INFINITE_ACCURACY`; if target is `INORGANIC`, `Swarm`, `Bee`, `Crab`, `Spinner`, or `Scorpio`, adds bonus damage `augment.damageFactor(8+2*buffedLvl())` (≈+100% of base extra dmg vs those types); on hit (if target survives) applies `Vulnerable` for 3 turns; dispels hero `Invisibility`. |

---

## Summary / Cross-References

- **Seed → Potion mapping** (`Potion.SeedToPotion.types`, in `Potion.java`) is the canonical seed-identity table; mirrors `ItemSpriteSheet`/scrambled-appearance pipeline already documented in `reference_items_atlas.md` memory.
- **Hunger thresholds**: `HUNGRY=300`, `STARVING=450` (from `actors/buffs/Hunger.java`) — all food `energy` values should be expressed against these constants for parity.
- **Trinket "buffedLvl()"**: trinkets can be temporarily boosted by external buffs beyond their stored `level()`; all formulas above use `buffedLvl()`, not raw `level()`.
- Two trinket upgrade-cost curves exist; verify each trinket's curve against `upgradeEnergyCost()` override before implementing a shared formula.
