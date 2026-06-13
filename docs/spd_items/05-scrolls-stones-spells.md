# Scrolls, Runestones, and Spells — SPD Reference

Source: `core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/{scrolls,stones,spells}/`
Strings: `core/src/main/assets/messages/items/items.properties`

All scroll/stone/spell logic runs on `Dungeon.hero`/`curUser`; multiplayer port must adapt to per-player triggering.

---

## 1. Scroll base mechanics (`Scroll.java`)

- 12 standard scrolls share a shuffled "rune name" pool (KAUNAN, SOWILO, LAGUZ, YNGVI, GYFU, RAIDO, ISAZ, MANNAZ, NAUDIZ, BERKANAN, ODAL, TIWAZ) until identified. The rune↔sprite mapping is randomized once per run (`ItemStatusHandler`).
- `TIME_TO_READ = 1.0` turn to read.
- Reading blocked if: `MagicImmune` buff active, `Blindness` buff active, or hero holds a cursed Unstable Spellbook (`bookRecharge` cursed) — except `ScrollOfRemoveCurse`/`ScrollOfAntiMagic` always work.
- `value() = 30 * quantity` (gold, default for unidentified-sellable scrolls; overridden per scroll).
- `energyVal() = 6 * quantity` (alchemy energy from Alchemize, default).
- `talentFactor` / `talentChance`: probability and strength multiplier for on-scroll-use talents (`Talent.onScrollUsed`). Default 1/1.
- **Scroll → Runestone recipe** (`Scroll.ScrollToStone`): consumes 1 scroll of a "downgrade" type, produces 2x matching runestone, cost 0g. Mapping:

| Scroll | → Runestone |
|---|---|
| Identify | Intuition |
| Lullaby | Deep Sleep |
| Magic Mapping | Clairvoyance |
| Mirror Image | Flock |
| Retribution | Blast |
| Rage | Aggression |
| Recharging | Shock |
| Remove Curse | Detect Magic |
| Teleportation | Blink |
| Terror | Fear |
| Transmutation | Augmentation |
| Upgrade | Enchantment |

---

## 2. Standard Scrolls (12)

| Scroll | Icon enum | value() | energyVal() | Key buff/effect |
|---|---|---|---|---|
| Upgrade | SCROLL_UPGRADE | 50 (known) | 10 (known) | upgrades item by +1 |
| Identify | SCROLL_IDENTIFY | 30 (known) | 6 (default) | identifies one item |
| Remove Curse | SCROLL_REMCURSE | 30 (known) | 6 | uncurses item(s) |
| Mirror Image | SCROLL_MIRRORIMG | 30 (known) | 6 | 2 mirror images |
| Recharging | SCROLL_RECHARGE | 30 (known) | 6 | `Recharging` buff 30 turns |
| Teleportation | SCROLL_TELEPORT | 30 (known) | 6 | teleport hero |
| Lullaby | SCROLL_LULLABY | 40 (known) | 6 | `Drowsy` 5 turns, AoE |
| Magic Mapping | SCROLL_MAGICMAP | 40 (known) | 6 | reveals level layout |
| Rage | SCROLL_RAGE | 40 (known) | 6 | beckons + `Amok` 5s |
| Retribution | SCROLL_RETRIB | 40 (known) | 6 | self-harm nova |
| Terror | SCROLL_TERROR | 40 (known) | 6 | `Terror` 20 turns AoE |
| Transmutation | SCROLL_TRANSMUTE | 50 (known) | 10 (known) | item → different item of same type |

If not yet known, `value()`/`energyVal()` fall back to the base `Scroll` defaults (30g / 6 energy).

### 2.1 Scroll of Upgrade
- `unique = true`. `talentFactor = 2`.
- Opens `WndUpgrade`; applies `item.upgrade()` (+1 level).
- Weapon/Armor: tracks `cursed`, `enchantHardened`, curse-enchant/glyph state before/after. If a curse enchant/glyph is fully removed by the upgrade → `removeCurse()` (full cleanse, validates Cleric unlock). If just `cursed` flag clears (no curse enchant) → `weakenCurse()` (partial, message only).
- If enchant/glyph was "hardened" and gets erased → warning "hardening_gone". If a "good" enchant/glyph becomes incompatible at new level → "incompatible" warning.
- Wand/Ring: clears `cursed` via `removeCurse()` if it was cursed and becomes uncursed.
- Always: `Degrade` buff detached, `Statistics.upgradesUsed++`, validates Mage unlock & item-level-acquired badges.

### 2.2 Scroll of Identify
- Fully identifies one selected unidentified item (`item.identify()`).
- If `ShardOfOblivion.passiveIDDisabled()` is active: instead of identifying, sets item to "ID ready" state (deferred identify) for Weapon/Armor/Ring/Wand.
- `usableOnItem`: any non-identified item.

### 2.3 Scroll of Remove Curse
- **Special case**: if a `TormentedSpirit` mob is in an adjacent cell (8-neighbour), reading the scroll instead frees/cleanses that spirit (`spirit.cleanse()`), consumes the scroll, no item selection.
- Otherwise opens item selector. `uncursable(item)`:
  - equipped item + hero has `Degrade` buff → true
  - Equipable/Wand: `cursed == true` OR (`!isIdentified() && !cursedKnown`)
  - Weapon: has curse enchantment
  - Armor: has curse glyph
- `uncurse()`: sets `cursedKnown=true`, clears `cursed`, removes curse enchant (`enchant(null)`)/glyph (`inscribe(null)`), updates wand level. Also clears hero's `Degrade` buff. Returns whether anything actually changed ("procced").
- Procc → `cleansed` message + `ShadowParticle.UP` x10 + validates Cleric unlock; else "not_cleansed".

### 2.4 Scroll of Mirror Image
- Spawns `NIMAGES = 2` `MirrorImage` NPCs in empty passable cells among the hero's 9-neighbourhood (self + 8 dirs).
- Each `MirrorImage`: HP=HT=1, `defenseSkill=1`, ally alignment, state=HUNTING, acts before other mobs (`actPriority = MOB_PRIO+1`).
  - `damageRoll()` = `(heroWeaponDamage + 1) / 2` (half hero damage, rounded up; uses Ring of Force if unarmed).
  - `attackSkill` = `(9 + heroLvl) * RingOfAccuracy multiplier * weapon accuracyFactor`.
  - `defenseSkill` = `baseDefense * (heroBaseEvasion + heroActualEvasion) / 2` — half of hero's evasion bonus applies.
  - `drRoll()` adds `NormalIntRange(0, weaponDefenseFactor/2)`.
  - Immune to ToxicGas, CorrosiveGas, Burning, AllyBuff. Starts with `MirrorInvis` (Invisibility, unannounced, `Short.MAX_VALUE` duration — breaks on first attack).
  - Triggers weapon procs and Holy Weapon/Body Form effects like the hero would.
- Spawn count returned; "no_copies" message if 0 spawned (no free adjacent cells).

### 2.5 Scroll of Recharging
- `Buff.affect(curUser, Recharging.class, Recharging.DURATION)` — `DURATION = 30` turns. Recharging buff accelerates wand charge regen during this window.
- Immediately bursts 15 `EnergyParticle`s (cosmetic "charge now" effect, not an instant full recharge).

### 2.6 Scroll of Teleportation
- `teleportPreferringUnseen(hero)`:
  - On `RegularLevel`: gathers all passable, unvisited, non-secret, unoccupied cells inside non-locked `SpecialRoom`s + general rooms. If any found, picks random one; if it's the entrance of a `SpecialRoom`/`SecretRoom`, may instead land just outside the door and reveal a secret door.
  - If no unseen candidates, falls back to `teleportChar` (fully random reachable cell, retried up to 20 times, avoiding secret cells).
  - On non-regular levels (`teleportInNonRegularLevel`): preference order `notSeen > notVisible > visible` reachable cells (respecting `LARGE` property + `openSpace`).
- Fails (`no_tele`) if target `Char.Property.IMMOVABLE` or immune to teleport source.
- On success: `Buff.detach(ch, Roots.class)`, occupies cell, plays TELEPORT sound, `Dungeon.observe()`.

### 2.7 Scroll of Lullaby
- All mobs in hero FOV get `Drowsy` for `Drowsy.DURATION = 5` turns; hero also gets `Drowsy` for 5 turns.
- `Drowsy` is restorative (heals) for allies/hero, but eventually causes sleep for hostiles (see exotic Siren's Song for charm variant).

### 2.8 Scroll of Magic Mapping
- Marks every `discoverable` cell as `mapped = true`.
- For any cell with `Terrain.SECRET` flag: calls `Dungeon.level.discover(i)`; if also in hero FOV, plays discover VFX (`Speck.DISCOVER`) and SECRET sound.
- Does **not** reveal mob/item locations — only terrain layout + secret doors/traps.

### 2.9 Scroll of Rage
- All mobs on level: `mob.beckon(curUser.pos)` (drawn toward reader).
- Non-ally mobs in hero FOV additionally get `Amok` buff for 5 turns (`Buff.prolong`, enrage — attacks anything nearby including other mobs).
- Plays CHALLENGE sound + `Speck.SCREAM`.

### 2.10 Scroll of Retribution
- Damage scaling: `hpPercent = (HT - HP) / HT`; `power = min(4.0, 4.45 * hpPercent)` — i.e. power reaches 4x (max) once hero HP drops to ~10% of max HT (since `4.45 * 0.10 ≈ 0.445`... actually `power=4` at `hpPercent ≈ 0.899`; capped at 4 once hpPercent ≥ ~0.899). Doc note: "scales 0x→1x maxing at ~10% HP" — full lethal scaling kicks in as HP approaches 0.
- Every mob in hero FOV (snapshot taken first): `damage = round(mob.HT/10 + mob.HP * power * 0.225)`. At power=4 this is `HT*0.1 + HP*0.9` — i.e. up to 90% of current HP plus 10% of max HP, capable of one-shotting low-HP enemies.
- Surviving mobs get `Blindness` for `Blindness.DURATION = 10` turns.
- Reader always gets `Weakness` (`Weakness.DURATION = 20`) and `Blindness` (10 turns), regardless of mob outcomes.
- White screen flash + BLAST sound.

### 2.11 Scroll of Terror
- Non-ally mobs in hero FOV get `Terror` buff (`Terror.DURATION = 20` turns), `object = curUser.id()` (so attacking the source shortens it).
- Message varies: 0 affected → "none"; 1 → names the fleeing mob; 2+ → "many monsters flee".
- Red `Flare` VFX (radius 5, alpha 32... actually `new Flare(5,32)`).

### 2.12 Scroll of Transmutation
- `unique=false`, `talentFactor=2`. `bones=true` (can drop in bones file).
- **Eligibility** (`usableOnItem`):
  - MeleeWeapon: yes, except Pickaxe on a `MiningLevel`
  - MissileWeapon: yes except plain `Dart`
  - Potion: yes except `Elixir`/`Brew`
  - Scroll: yes except itself (unless qty>1 or `identifiedByUse`)
  - Artifact: yes unless `unique`
  - Else: Ring, Wand, Trinket, `Plant.Seed`, `Runestone`
- **Transformation rules** (`changeItem`):
  - `MagesStaff` → re-rolls its imbued wand to a different random wand class, levels reset to 0, identified.
  - `TippedDart` → different random tipped-dart type (same count).
  - Melee/Missile weapon → random weapon of same tier/category (excluding current class & challenge-blocked); preserves `trueLevel` (upgrade/degrade), `enchantment`, `curseInfusionBonus`, `masteryPotionBonus`, ID/curse flags, `augment`, `enchantHardened`. For missile weapons, tracks old set as fully "used up" and applies durability carryover.
  - Ring → random different ring, preserves level (up/degrade) + ID/curse flags.
  - Artifact → random different non-blocked artifact, preserves curse/ID flags and `transferUpgrade(visiblyUpgraded())`. If no artifact available, **converts to a Ring** instead: ring level = 2 if artifact was visibly upgraded to 10, 1 if ≥5, else 0; preserves ID/curse flags. (Special case for `DriedRose`: drops its ghost weapon/armor on the floor first.)
  - Trinket → random different trinket, preserves `trueLevel`, ID/curse flags.
  - Wand → random different wand, level 0 then `upgrade(trueLevel)`, preserves charges, `curseInfusionBonus`, `resinBonus`, ID/curse flags.
  - `Plant.Seed` → random different seed.
  - `Runestone` → random different runestone.
  - Scroll ↔ ExoticScroll: maps via `ExoticScroll.regToExo` / `exoToReg` (regular ↔ exotic counterpart, see §4 table).
  - Potion ↔ ExoticPotion: analogous mapping.
- Equipped items: auto re-equip the new item (handles second-weapon slot specially); quickslot binding preserved.
- `value() = 50` (known) / `energyVal() = 10` (known).

---

## 3. Exotic Scrolls (`items/scrolls/exotic/`)

`ExoticScroll` base: shares ID state with its "regular" counterpart (`exoToReg`/`regToExo` maps). `value() = regularCounterpart.value() + 30` (per unit); `energyVal() = regularCounterpart.energyVal() + 6`.

**Regular ↔ Exotic mapping** (also crafting recipe `ScrollToExotic`: 1 regular scroll + 6 energy → 1 exotic):

| Regular | Exotic |
|---|---|
| Upgrade | Enchantment |
| Identify | Divination |
| Remove Curse | Anti-Magic |
| Mirror Image | Prismatic Image |
| Recharging | Mystical Energy |
| Teleportation | Passage |
| Lullaby | Siren's Song |
| Magic Mapping | Foresight |
| Rage | Challenge |
| Retribution | Psionic Blast |
| Terror | Dread |
| Transmutation | Metamorphosis |

### 3.1 Scroll of Anti-Magic
- `Buff.affect(curUser, MagicImmune.class, MagicImmune.DURATION)` — `DURATION = 20` turns.
- Blocks all magical effects (wands, scrolls, rings, artifacts, enchantments, curses) on the hero for the duration. Heroic armor abilities still work.

### 3.2 Scroll of Challenge
- All mobs on the level `beckon(curUser.pos)`.
- Applies `ChallengeArena` buff (`DURATION = 100` turns):
  - Arena radius (`dist`) computed via shadowcasting from reader's position:
    - On floors 5/10/20 (boss floors): `dist = 1` (small arena).
    - Otherwise: count visible cells via `ShadowCaster.castShadow(... radius 8)`; if `<30` visible cells → `dist=1`; `≥100` → `dist=3`; else `dist=2`.
  - `PathFinder.buildDistanceMap(pos, passable|avoid, dist)` defines arena cell set.
  - While standing in arena: 33% damage reduction (applied before other DR sources) + no hunger increase.
  - Buff ticks down `left` each turn; detaches if reader leaves arena cells or `left <= 0`.
- CHALLENGE sound + `Speck.SCREAM`.

### 3.3 Scroll of Divination
- Randomly identifies up to 4 unknown item "types" (potion color, scroll rune, or ring gem) — not necessarily items the hero is carrying.
- Weighted selection: `baseProbs = {3,3,3}` for {potions, scrolls, rings}; each pick decrements that category's remaining weight by 1 (within the loop) but resets to `baseProbs` clone every successful pick (the decrement only affects retries within the same iteration when a category is exhausted).
- Stops early if no unknown items remain in any category ("nothing_left" message).
- Shows `WndDivination` listing the identified item types.

### 3.4 Scroll of Dread
- For each non-ally mob in hero FOV:
  - If not immune to `Dread` → applies `Dread` buff (no fixed duration param — uses `Dread`'s own default `DURATION = 20`, internally tracked via `left` countdown), `object = curUser.id()`.
  - If immune to `Dread` → falls back to regular `Terror` for `Terror.DURATION = 20`.
- `Dread`-affected mobs flee permanently off the level (don't just recover after the timer like Terror — they path off-map and despawn). Strong-willed/boss enemies get Terror instead.
- Red `Flare` VFX.

### 3.5 Scroll of Enchantment
- `unique = true`, `talentFactor = 2`.
- `enchantable(item)`: Weapon or Armor, and (`isUpgradable()` or is a `SpiritBow`).
- Presents 3 random enchantment/glyph choices:
  - Weapon: `enchants[0] = randomCommon(existing)`, `enchants[1] = randomUncommon(existing)`, `enchants[2] = random(existing, excluding [0],[1])`.
  - Armor: same pattern with `Armor.Glyph`.
- Selecting one calls `weapon.enchant(choice)` / `armor.inscribe(choice)` — replaces any existing enchant/glyph (including curses).
- Cancelling (if scroll was identified-by-use) prompts a consume-confirmation (`cancel_warn`), since the scroll is consumed regardless.

### 3.6 Scroll of Foresight
- `Buff.affect(curUser, Foresight.class, Foresight.DURATION)` — `DURATION = 400` turns.
- While active: continuously reveals nearby terrain detail, including hidden doors/traps (removes need to search).

### 3.7 Scroll of Metamorphosis
- `talentFactor = 2`.
- Opens `WndMetamorphChoose`: pick one of the hero's current class talents (only base class talents, not subclass/armor-ability talents; only talents the hero can actually use).
- Then `WndMetamorphReplace`: for the chosen talent's tier, offers up to 5 replacement talent options — one randomly drawn per `HeroClass` (excluding the hero's own class talents already present at that tier, and excluding the talent being replaced if it exists in that class's set).
- Swaps the talent; points invested carry over (`Dungeon.hero.pointsInTalent(replacing)` transferred to new talent). Triggers `Talent.onTalentUpgraded` if applicable.
- Cancellation (if not yet identified) consumes the scroll regardless.

### 3.8 Scroll of Mystical Energy
- `Buff.affect(curUser, ArtifactRecharge.class).set(30)` with `ignoreHornOfPlenty = false` — charges equipped artifacts over **30** turns (cf. `ScrollOfRecharging`'s 30-turn wand recharge).
- Also calls `ScrollOfRecharging.charge(curUser)` for the cosmetic energy burst.

### 3.9 Scroll of Passage
- Instantly teleports to the nearest region's first floor (`returnDepth = max(1, depth - 1 - (depth-2) % 5)`, branch 0) via `InterlevelScene.Mode.RETURN`.
- Fails silently with `no_tele` message if `!Dungeon.interfloorTeleportAllowed()`.
- Useful for quickly returning to a shop floor.

### 3.10 Scroll of Prismatic Image
- If a `PrismaticImage` ally already exists (on level or in Stasis): fully heals it to `HT` instead of creating a new one (shows healing floating text).
- Otherwise: `Buff.affect(curUser, PrismaticGuard.class).set(PrismaticGuard.maxHP(curUser))`.
  - `PrismaticGuard.maxHP(hero) = 10 + floor(hero.lvl * 2.5)` — i.e. roughly half the hero's max HP.
  - `PrismaticImage` (when later summoned via this guard mechanism): `HP=HT=10` base; `damageRoll = NormalIntRange(2 + heroLvl/4, 4 + heroLvl/2)`; defense/evasion mirrors hero's stats (same formula family as `MirrorImage`).
- Description: "weaker clone with similar defence but lower HP/damage"; shows itself only when enemies present, defends the reader.

### 3.11 Scroll of Psionic Blast
- White screen flash + BLAST sound.
- Every mob in hero FOV (snapshot first): `damage = round(mob.HT/2 + mob.HP/2)`. This **always kills non-resistant enemies** (since `HT/2+HP/2 ≥ HP` when `HP ≤ HT`, i.e. damage ≥ current HP always — true one-shot for anything without explicit resistance to this scroll's damage type). Survivors (resistant mobs) get `Blindness` (10 turns).
- Self-damage: `curUser.damage(round(HT * 0.5 * 0.9^targets.size()), this)`. More targets hit → less self-damage (each target reduces the multiplier by factor 0.9). 0 targets → 50% of max HT self-damage.
- If reader survives: `Blindness` (10 turns) + `Weakness` for `Weakness.DURATION * 5 = 100` turns, `Dungeon.observe()`.
- If reader dies: counts as "death from friendly magic" badge, `Dungeon.fail(this)`, message "The Psionic Blast tears your mind apart...".

### 3.12 Scroll of Siren's Song
- Targeted (cell selector). Requires a target unless already identified (anonymous/known scrolls can be read with no valid target → "activates without a target").
- All non-ally mobs in hero FOV **except the chosen target** get `Charm` buff (`Charm.DURATION = 10` turns), `object = curUser.id()`.
- Chosen target (must be non-ally `Mob`):
  - If not immune to `Enthralled` → `AllyBuff.affectAndLoot(target, curUser, Enthralled.class)` — **permanently** converts target into an ally (loot is granted to the player as if killed).
  - If immune → falls back to `Charm` (10 turns) like the other mobs.
- `Enthralled` is a negative `AllyBuff` (from the mob's perspective) shown with heart icons; permanent ally that fights enemies encountered.
- Plays CHARMS sound + delayed LULLABY sound; `Speck.HEART` particles.

---

## 4. Runestones (`items/stones/`)

`Runestone` base:
- `stackable = true`, `defaultAction = AC_THROW` (thrown, not used from inventory, except `InventoryStone` subclasses).
- `value() = 15 * quantity`, `energyVal() = 3 * quantity`.
- `isUpgradable() = false`, `isIdentified() = true` always (runestones are never "unidentified" — they have fixed appearance/names).
- On throw: if hero is `MagicImmune`, or thrown into a pit with no target, behaves like a normal thrown item (no activation). Otherwise: `Talent.onRunestoneUsed`, `activate(cell)`, presses the cell (triggers traps), dispels invisibility.
- `Runestone.PlaceHolder`: generic unidentified-stone stand-in.

> Note: `items.stones.stoneofdisarming.*` strings exist in `items.properties` but **no `StoneOfDisarming.java` exists** in the current source tree — appears to be a removed/unimplemented stone (only `levels/traps/DisarmingTrap.java` remains). Described effect per strings: "disarm up to 9 traps around impact area." Treat as unimplemented/legacy for the port.

| Stone | Effect | Radius/Mechanic |
|---|---|---|
| Enchantment | Adds enchantment/glyph to weapon/armor (same selection UI as Scroll of Enchantment) | inventory-use (`InventoryStone`), `unique=true`, value 30, energy 5 |
| Intuition | Guess unidentified item's type; correct guess = full ID | 2 uses per stone (tracked via `IntuitionUseTracker` buff — 1st use doesn't consume, 2nd does) |
| Detect Magic | Reveals if item has positive/negative/both/no magic | sets `cursedKnown=true`; inventory-use |
| Flock | Summons sheep around impact | `PathFinder` dist-2 from impact cell; spawns `Sheep` (init HP=8) on every valid non-solid, unoccupied, non-pit cell within range |
| Shock | Lightning AoE: paralyzes + charges wand | dist-2 from impact; each hit char gets `Paralysis` for 1 turn; `curUser.belongings.charge(1 + hits)` — wand charge scales with number of targets hit |
| Blink | Teleports thrower to impact location | uses `Ballistica.PROJECTILE` throw path; if a char occupies target cell, lands one tile short along the path; calls `ScrollOfTeleportation.teleportToLocation` |
| Deep Sleep | Puts target mob into permanent magical sleep | `MagicalSleep` buff — only affects `Mob`; sleep lasts until disturbed (no fixed duration; `paralysed++` while active) |
| Clairvoyance | Reveals wide area through walls | `DIST = 20` tile radius circular reveal via `ShadowCaster.rounding`; marks `mapped=true`; also discovers secret cells in range (with SECRET sound if any found) |
| Aggression | All nearby enemies prefer attacking the targeted character | `Aggression` buff, `DURATION = 20` turns normally, `DURATION/4 = 5` turns if target is BOSS/MINIBOSS |
| Blast | Instant explosion at impact (like a bomb) | `new Bomb.ConjuredBomb().explode(cell)` — standard bomb explosion: range via `explosionRange()` (default 2), damage `NormalIntRange(4+scalingDepth, 12+3*scalingDepth)` to chars in blast, destroys flammable terrain |
| Fear | Targeted char flees (Terror) | `Terror.DURATION = 20` turns; only affects non-ally chars; `object = curUser.id()` (attacking shortens it) |
| Augmentation | Reconfigure weapon/armor augment | Weapon: Speed ↔ Damage (also affects thrown-weapon durability inversely with speed); Armor: Defense ↔ Evasion. Also calls `ScrollOfUpgrade.upgrade()` for the VFX (no actual level change). Inventory-use, value 30, energy 5 |

### 4.1 Stone of Enchantment / Augmentation (InventoryStone details)
- Both are `InventoryStone` (not thrown) with `preferredBag = Backpack`.
- Stone of Enchantment: `unique=true`; calls `weapon.enchant()` / `armor.inscribe()` with no argument (random new enchant/glyph — contrast with Scroll of Enchantment's player-choice UI).
- Stone of Augmentation: `WndAugment` lets player pick "Speed"/"Damage" (weapon) or "Evasion"/"Defense" (armor), or "Remove Augmentation". Sets `item.augment = chosen`.

### 4.2 Stone of Intuition detail
- `usableOnItem`: unidentified Ring, Potion, or Scroll (incl. exotic — guesses map to the exotic class via `exoToReg`/`regToExo`).
- `WndGuess` shows icon buttons for every unidentified class in that category; correct guess → `item.identify()` (or `ring.setKnown()`); incorrect → message only, stone still consumed per the 2-use rule.

### 4.3 Stone of Aggression detail
- `Aggression` buff is `FlavourBuff`, type `NEGATIVE`, `announced=true`, icon `BuffIndicator.TARGETED`.
- On detach: if target is an enemy, clears any mob `aggro()` pointing at/from it (resets enemy-vs-enemy targeting caused by the aggression effect).

---

## 5. Spells (`items/spells/`)

`Spell` base:
- `stackable=true`, `defaultAction = AC_CAST`.
- Casting blocked entirely if hero has `MagicImmune` ("no_magic" message, no effect/consumption).
- `isIdentified() = true` always; `isUpgradable() = false`.
- Most spells are crafted via `Recipe.SimpleRecipe` (alchemy: N inputs + cost in energy → `outQuantity` spells).

| Spell | Recipe inputs → cost → output qty | value() | energyVal() |
|---|---|---|---|
| Alchemize | Seed + Runestone → 2 energy → 8 | `20 * (qty/8)` | `4 * (qty/8)` |
| Beacon of Returning | 1× Scroll of Passage → 12 energy → 5 | `60 * (qty/5)` | `12 * (qty/5)` |
| Curse Infusion | 1× Scroll of Remove Curse + 1× Metal Shard → 6 energy → 4 | `60 * (qty/4)` | `12 * (qty/4)` |
| Magical Infusion | 1× Scroll of Upgrade → 12 energy → 1 | 60 | 12 |
| Phase Shift | 1× Scroll of Teleportation → 10 energy → 6 | `60 * (qty/6)` | `12 * (qty/6)` |
| Reclaim Trap | 1× Scroll of Magic Mapping + 1× Metal Shard → 8 energy → 5 | `60 * (qty/5)` | `12 * (qty/5)` |
| Recycle | 1× Scroll of Transmutation → 12 energy → 12 | `60 * (qty/12)` | `12 * (qty/12)` |
| Summon Elemental | 1× Embers → 10 energy → 6 | (uses Spell default) | (uses Spell default) |
| Telekinetic Grab | 10× Liquid Metal → 10 energy → 8 | `50 * (qty/8)` | `10 * (qty/8)` |
| Unstable Spell | special (1 scroll-class ingredient + 1 runestone, see below) → 1 energy → 1 | 40 | 8 |
| Wild Energy | 1× Scroll of Recharging + 1× Metal Shard → 4 energy → 5 | `60 * (qty/5)` | `12 * (qty/5)` |

### 5.1 Alchemize
- Opens item selector for any item that's sellable (`Shopkeeper.canSell`) or has `energyVal() > 0`.
- `WndAlchemizeItem` offers: sell for gold (full stack price), or "energize" (convert to alchemy energy) — single item or split 1-vs-all for stacks.
- **Side-effect**: converting potions/scrolls to energy via this spell **identifies them** (per description).
- `talentChance = 1/8` (matches `OUT_QUANTITY`).

### 5.2 Beacon of Returning
- Two modes via `WndOptions` ("Set" / "Return") once a beacon location exists, otherwise auto-"Set".
- **Set**: records `Dungeon.depth`, `Dungeon.branch`, `hero.pos` into `BeaconTracker` buff (`revivePersists=true`); adds a journal landmark note; costs 1 turn; does NOT consume the item.
- **Return**: 
  - Same floor+branch as beacon: pushes any blocking char out of the way (prefers pushing non-immovable chars), then `ScrollOfTeleportation.teleportToLocation`. Spends 1 turn.
  - Different floor: requires `Dungeon.interfloorTeleportAllowed()`; blocked if beacon is on a Mining level (depth 11-14, branch 1); switches to `InterlevelScene.Mode.RETURN`.
  - **Consumes 1 charge** of the spell stack on successful return; if `quantity==1` after, removes the landmark note and detaches the tracker buff.
- Glows white (`ItemSprite.Glowing(0xFFFFFF)`) while a beacon location is set.

### 5.3 Curse Infusion
- `unique=false` but rare; `usableOnItem`: upgradable Equipable, Wand, or `SpiritBow`.
- Sets `item.cursed = true`. 
  - Weapon: if it already has an enchant, **only replaces it with a curse enchant if the existing enchant is "good" or already curse-infusion-boosted** — otherwise applies `randomCurse()` fresh. Sets `curseInfusionBonus = true` (grants the curse-infusion stat bonus, separate from a "natural" curse — does not stack across multiple infusions, lost if uncursed).
  - Armor: same logic with glyphs.
  - Wand: sets `curseInfusionBonus = true`, `updateLevel()`.
  - `RingOfMight`: triggers `curUser.updateHT(false)` (recompute max HP since Might affects it).
- ShadowParticle burst + CURSED sound.
- **Multiple infusions can re-roll/change the curse** on weapon/armor (per description).

### 5.4 Magical Infusion
- `unique=true`, `talentFactor=2`.
- Functionally `ScrollOfUpgrade` but:
  - If item has an existing enchant/glyph, calls `item.upgrade(true)` — the `true` flag means the enchant/glyph is **never erased** by this upgrade (unlike Scroll of Upgrade which can strip enchants at higher levels).
  - Preserves `cursed` flag and wand `curseInfusionBonus` through the upgrade.
  - Also calls `Degrade.detach()` and `ScrollOfUpgrade.upgrade()` (VFX only).
- Same `WndUpgrade` UI as Scroll of Upgrade.

### 5.5 Phase Shift
- `TargetedSpell`, `usesTargeting=true`, magic-missile bolt VFX.
- Teleports the targeted char (`ScrollOfTeleportation.teleportChar`, random-reachable-cell variant since target isn't the hero necessarily).
- If target was a hunting `Mob`, resets to `WANDERING` and `beckon`s it to a random destination (disorientation).
- Applies `Paralysis` (`Paralysis.DURATION`) to the teleported char **unless** it has `BOSS` or `MINIBOSS` property (bosses resist the stun).
- Can target self.

### 5.6 Reclaim Trap
- `TargetedSpell`. Two-phase item:
  - **Phase 1** (no trap stored): target an active, visible trap → disarms it (even traps normally "permanent"/undisarmable), plays LIGHTNING sound, `ScrollOfRecharging.charge(hero)` (cosmetic), stores `trap.getClass()` in `ReclaimedTrap` buff on the hero. **Not consumed** — spends `timeToCast()` but doesn't detach the item.
  - **Phase 2** (trap stored): target any cell → spawns a new instance of the stored trap class at that cell (`reclaimed=true`), activates it immediately, consumes the spell charge.
  - Only one trap can be stored at a time.
- `desc()` dynamically shows which trap is currently loaded.
- Glowing color matches the stored trap's `color` field (9-color palette by trap type).

### 5.7 Recycle
- `usableOnItem`: Potion (not Elixir/Brew), Scroll (incl. exotic), `Plant.Seed`, `Runestone`, `TippedDart`.
- Produces one random item of the **same category** but a **different specific class** than the input (loop until different & not challenge-blocked):
  - Potion → random potion (mapped back to exotic if input was exotic).
  - Scroll → random scroll (mapped back to exotic if input was exotic).
  - Seed → random seed.
  - Runestone → random runestone.
  - TippedDart → `TippedDart.randomTipped(1)`.
- Drops result on the floor if inventory full. `talentFactor=2`.

### 5.8 Summon Elemental
- Two actions: `CAST` (summon/recall) and `IMBUE` (power up via item selector).
- **Cast**: 
  - If an `Elemental` ally already exists with `InvisAlly` buff (i.e., previously summoned and currently "stowed"/invisible), it's recalled (`ScrollOfTeleportation.appear` near hero) and set to `HUNTING`. Costs 1 tick, **no item consumed**.
  - Else: spawns new `Elemental` of `summonClass` (default `Elemental.AllyNewBornElemental`), full HP, `InvisAlly` buff, appears near hero. **Consumes** the item.
  - Fails with "no_space" if no free adjacent cell.
- **Imbue** (`IMBUE` action, item selector): consuming one of:
  - Identified `PotionOfLiquidFlame` → `summonClass = FireElemental` (orange glow `0xFFBB33`)
  - Identified `PotionOfFrost` → `summonClass = FrostElemental` (cyan glow `0x8EE3FF`)
  - Identified `ScrollOfRecharging` → `summonClass = ShockElemental` (yellow glow `0xFFFF85`)
  - Identified `ScrollOfTransmutation` → `summonClass = ChaosElemental` (white/translucent `0xE3E3E3` @ 0.5 alpha)
  - Re-imbuing replaces the previous imbue (only one type active at a time). A "newborn" elemental (unimbued) has no ranged attack.
- Only **one elemental can exist at a time** (recast just teleports it back).

### 5.9 Telekinetic Grab
- `TargetedSpell`, `timeToCast() = 0` (time charged based on actual pickups, not the cast itself).
- If target char has a `PinCushion` buff (stuck thrown weapons): grabs all of them one by one.
- Else if target cell has an item `Heap`: 
  - If `Heap.Type != HEAP` (e.g., a chest/special container) → cannot grab, "cant_grab" + spends 1 tick.
  - Else picks up everything in the heap.
- Total pickup time accumulated; if `>1` turn, hero is refunded `(totalTime - 1)` (i.e., the cast itself costs at most 1 turn regardless of how many items grabbed).
- "no_target" + spends 1 tick if nothing to grab.
- Special case: can grab items from `DwarfKing` while he's seated on his throne (`solid` tile) — checks one tile past the bolt's collision point.

### 5.10 Unstable Spell
- Triggers the effect of a **random standard scroll** (weighted), auto-identified-as-anonymous (`s.anonymize()`, doesn't consume hero's scroll-ID progress).
- Scroll selection weights (`Random.chances`): Identify 3, {RemoveCurse, MagicMapping, MirrorImage, Recharging, Lullaby, Retribution, Rage, Teleportation, Terror} each 2, Transmutation 1.
- **Context-sensitive reroll**:
  - If hero sees **0 enemies**: rerolls until the scroll is in `nonCombatScrolls` = {Identify, RemoveCurse, MagicMapping, Recharging, Lullaby, Teleportation, Transmutation}.
  - If hero sees **≥1 enemy**: rerolls until in `combatScrolls` = {MirrorImage, Recharging, Lullaby, Retribution, Rage, Teleportation, Terror}.
  - (Recharging and Lullaby and Teleportation appear in both lists.)
- Crafting recipe is unusual: any 1 scroll-or-exotic-scroll class (from `regToExo` key/value sets) + any 1 runestone, cost 1 energy → 1 Unstable Spell.

### 5.11 Wild Energy
- `TargetedSpell`, `usesTargeting=true`. Uses `CursedWand.cursedZap` for its bolt VFX (shared with cursed-wand "random effect" visuals).
- On hit:
  - `ScrollOfRecharging.charge(hero)` cosmetic burst.
  - `hero.belongings.charge(1f)` — charges all wands by 1.
  - `ArtifactRecharge.chargeArtifacts(hero, 4f)` — charges artifacts by 4 "ticks" immediately.
  - `Buff.affect(hero, Recharging.class, 8f)` and `Buff.affect(hero, ArtifactRecharge.class).extend(8)` — extends recharge buffs by 8 turns.
- Despite being aimed, doesn't damage the target — "you choose a direction for this cursed magic to shoot in" is purely the cursed-wand-style VFX; the actual recharge effect applies to the **caster**, not the target.

---

## 6. Relevant buff durations (for cross-reference)

| Buff | Duration | Used by |
|---|---|---|
| `Recharging.DURATION` | 30 | Scroll of Recharging, Wild Energy (8 via `affect`, separately) |
| `Drowsy.DURATION` | 5 | Scroll of Lullaby |
| `Terror.DURATION` | 20 | Scroll of Terror, Scroll of Dread (fallback), Stone of Fear |
| `Weakness.DURATION` | 20 | Scroll of Retribution (1x), Scroll of Psionic Blast (5x = 100) |
| `Blindness.DURATION` | 10 | Scroll of Retribution, Scroll of Psionic Blast |
| `MagicImmune.DURATION` | 20 | Scroll of Anti-Magic |
| `Foresight.DURATION` | 400 | Scroll of Foresight |
| `Charm.DURATION` | 10 | Scroll of Siren's Song (non-target mobs) |
| `Dread.DURATION` | 20 (internal `left`) | Scroll of Dread |
| `Aggression.DURATION` | 20 (5 for boss/miniboss) | Stone of Aggression |
| `ChallengeArena.DURATION` | 100 | Scroll of Challenge |
| `PrismaticGuard.maxHP(hero)` | `10 + floor(lvl*2.5)` | Scroll of Prismatic Image |

---

## 7. Open questions for the port

- StoneOfDisarming has localization strings but no implementing class — confirm whether to implement it (per strings: disarm up to 9 traps in an area) or treat as cut content.
- Scroll of Divination's probability algorithm has a subtle quirk (per-category weight only decrements within retry loop, resets to base on each successful pick) — verify exact replication is desired vs. a simplified "pick 4 random unknown items across categories" for the port.
- Many spells reference multiplayer-incompatible singletons (`Dungeon.hero`, `curUser`, `Stasis.getStasisAlly()`) — port must scope these per-player.
