# Line of Sight / FOV — SPD Source Reference

Source: `shattered-pixel-dungeon/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/`
(`mechanics/ShadowCaster.java`, `levels/Level.java`, `levels/Terrain.java`, `Dungeon.java`, `actors/Char.java`,
relevant buffs in `actors/buffs/`)

## Core algorithm (`ShadowCaster.castShadow`)
- Recursive shadowcasting (roguebasin algorithm), operating on flat `boolean[]` arrays indexed `y*w+x`.
- `MAX_DISTANCE = 20`. Distance is `Math.round(viewDist)`, clamped to 20.
- `fieldOfView` is cleared, source cell set `true`, then 8 octants scanned clockwise via `scanOctant` with mirror flags `(mX, mY, mXY)`.
- **`ROUNDING` table**: `rounding[i][j] = min(j, round(i * cos(asin(j/(i+0.5)))))` for `i,j` in `1..MAX_DISTANCE`. Per-row max column, makes FOV circular instead of square.
- **Distance-2 special case**: `rounding[2][2]` is forced to `2` (normally would be `1`) to fill in FOV corners at radius 2 — otherwise diagonal movement at close range is disproportionately punished.
- All slope math offset by `0.5` (testing cell centers); `start`/`end` columns computed with `floor(... + 0.499)` / `ceil(... - 0.499)` to handle slopes that just barely touch a cell.
- When a row's column hits a blocking cell:
  - First blocking cell in a run → spawn a recursive sub-scan one row deeper, ending at the left edge of that cell (`rSlope = (col-0.5)/(row+0.5)`), unless it's the very first column (`col == start`).
  - Cell stops being blocking → tighten `lSlope` to `(col-0.5)/(row-0.5)` for subsequent rows in this scan.
  - If a row *ends* while still in a blocking run, that octant scan terminates (`return`).
- Exception-safe: on any exception the whole FOV is blanked and the error reported.
- **This algorithm is ported 1:1** in `backend/app/engine/mechanics/shadowcaster.py` — already faithful, no gaps here.

## What blocks LOS — `Terrain.LOS_BLOCKING` flag
Per-tile flag baked into `Level.losBlocking[]` (rebuilt via `updateCellFlags` whenever a tile changes via `Level.set`):

| Terrain | LOS_BLOCKING? | Notes |
|---|---|---|
| `WALL`, `WALL_DECO`, `SECRET_DOOR` (renders as wall) | yes | + `SOLID` |
| `DOOR` (closed) | **yes** | + `PASSABLE`, `FLAMABLE`, `SOLID` — closed door blocks vision but you can walk into it to open it |
| `OPEN_DOOR` | **no** | plain passable, no LOS block |
| `LOCKED_DOOR`, `HERO_LKD_DR` | yes | + `SOLID` |
| `CRYSTAL_DOOR` | no (only `SOLID`) | see-through, blocks movement |
| `HIGH_GRASS`, `FURROWED_GRASS` | yes | + `PASSABLE`, `FLAMABLE` — see exceptions below |
| `BARRICADE`, `BOOKSHELF` | yes | + `FLAMABLE`, `SOLID` |
| Map edge (border ring) | yes | forced `losBlocking[i] = solid[i] = true` for the outermost row/col |
| Everything else (floor, water, grass, chasm, traps, statues, pedestal, doors-open, embers...) | no | |

- Doors: opening a door (`Door.java` → `Level.set(cell, OPEN_DOOR)`) flips `losBlocking[cell]` to `false` immediately via `updateCellFlags`; closing flips it back. No separate "door open" bookkeeping in the shadowcaster — it just reads the current terrain's flag.

## Per-tick blocking-map adjustments (`Level.updateFieldOfView`)
A fresh copy of `losBlocking` (`modifiableBlocking`) is only made if needed — base array is reused otherwise. Two conditional passes, evaluated **for the viewing character `c`** (could be hero or a mob with FOV, e.g. wards/lotus/spirit hawk allies):

1. **High grass becomes see-through** (LOS_BLOCKING cleared on `HIGH_GRASS`/`FURROWED_GRASS` cells) if:
   - `c` is a Hero with `HeroSubClass.WARDEN`, OR `c instanceof YogFist.SoiledFist`, OR `c instanceof GnollGeomancer`
   - **AND NOT** (level is `MiningLevel` and the Blacksmith fungi quest is active — grass stays opaque during that quest regardless of class).
   - Grass *itself* is still walkable/flammable; only the vision-blocking property is dropped. (Stealth bonus from standing in grass is a separate system, not part of FOV.)

2. **Smoke Screen blob becomes LOS-blocking** for any cell with `volume > 0`, if:
   - `c.alignment != ALLY` (i.e., affects hero & enemy mobs) **AND** `c` is not a `GnollGeomancer`
   - AND the level has an active `SmokeScreen` blob with total `volume > 0`.
   - This *adds* blocking on top of normal terrain (cells that weren't blocking become blocking); doesn't remove existing blocks.

## View distance (`Char.viewDistance`, default 8)
- Base `8` for all `Char`s. Overridden per-mob:
  - `Bee` → 4, `RotLasher` → 1
  - `Tengu`, `GnollGeomancer`, `YogDzewa` (phase-dependent: starts at level default, then ramps via its own `viewDistance` field 4→1 across phases, also forces `level.viewDistance` and hero's to match) → 12
  - `RipperDemon`, `YogFist`, `Succubus`, `Eye`, `YogDzewa` (late) → `Light.DISTANCE` (6)
- Level-level override `Level.viewDistance` (default 8, or **2** if `Challenges.DARKNESS` is active):
  - `PrisonBossLevel` → 12
  - `HallsLevel` → `min(26 - depth, viewDistance)` (shrinks as depth increases toward Halls bottom)
  - `HallsBossLevel`, `LastLevel` → 4
  - Water-level effect (`viewDistance = round(5*viewDistance/8)`) applied in two spots in `Level.java` (flooding-related reduction — confirm exact trigger if porting).
- **For the hero specifically**, `updateFieldOfView` does:
  ```
  viewDist = c.viewDistance
  if (c instanceof Hero) {
      viewDist *= 1 + 0.25 * pointsInTalent(FARSIGHT)        // Cleric talent, +25%/point
      viewDist *= EyeOfNewt.visionRangeMultiplier()           // artifact charge bonus
  }
  ```
- `Dungeon.hero.viewDistance` itself is set in `Dungeon.java:506`:
  ```
  hero.viewDistance = (light buff == null) ? level.viewDistance : max(Light.DISTANCE, level.viewDistance)
  ```
  i.e. the `Light` buff (torches/lantern/etc.) guarantees at least radius 6 regardless of level darkness, but doesn't reduce vision if the level is already brighter.
- `ShadowCaster.MAX_DISTANCE = 20` is the hard cap regardless of any multiplier.

## Blindness / can't-see-at-all states
`updateFieldOfView` computes:
```
sighted = (c.buff(Blindness) == null) && (c.buff(Shadows) == null) && c.isAlive()
```
- If **not** sighted (blinded, under `Shadows`/`Invisibility`-family darkness debuff, or dead): `fieldOfView` is entirely cleared (shadowcast skipped). Note `Shadows extends Invisibility` — it's an enemy-side "this char can't see" effect, not the hero's own invisibility.
- If sighted: normal shadowcast runs as above.

## "Sense" radius — discoverable tiles (blind/mind-vision fallback)
Independent of the shadowcast, a second pass adds tiles within a small **square-ish "sense" radius** (`sense`, default 1, i.e. just adjacent cells) from `Level.discoverable[]`:
- `discoverable[i]` is precomputed in `cleanWalls()`: true for any cell that has at least one of its 9 neighbours (`NEIGHBOURS9`) that is *not* `WALL`/`WALL_DECO` — i.e., any non-fully-enclosed-by-wall cell. This represents "you can tell this tile exists even if you can't see into it" (e.g., feel the wall next to you).
- This pass runs **if** `!sighted` (blind — gives you adjacent-tile awareness even blind) **or** `sense > 1` (mind vision/magical sight active, see below).
- `sense` is raised (hero only) by:
  - `MindVision` buff → `sense = max(buff.distance, sense)`
  - `MagicalSight` buff → `sense = max(MagicalSight.DISTANCE, sense)`
- The discoverable cells are copied row-by-row into `fieldOfView` using the same `rounding` table to keep the area roughly circular (left/right bounds derived from `rounding[sense][...]`).
- **Net effect**: blind characters still "see"/discover the cells immediately touching open space around them (lets you bump into walls/feel your way), even though they have zero true shadowcast vision.

## Mind Vision / Awareness / Divine Sense (hero only)
All of this *adds* mob-revealing cells to `heroMindFov` (separate static buffer, OR'd into `fieldOfView` at the end — does **not** unlock terrain visibility, just reveals char positions):
- **`MindVision` buff present**: every mob's 3×3 neighbourhood (`NEIGHBOURS9`) added to `heroMindFov`, regardless of distance (except stealthy neutral Mimics, which are skipped).
- **No `MindVision`**: compute `mindVisRange` from:
  - `HEIGHTENED_SENSES` talent (Rogue): `1 + pointsInTalent`
  - `DivineSense` buff (Cleric): `4 + 4*pointsInTalent(DIVINE_SENSE)` for Cleric, else `1 + 2*pointsInTalent` (for an ally under Power of Many's link)
  - `EyeOfNewt.mindVisionRange()` artifact bonus (takes the max)
  - For each mob within `mindVisRange` of hero (or of a Power-of-Many-linked ally with Divine Sense), if not already in `fieldOfView`, add its 3×3 neighbourhood to `heroMindFov` (skip stealthy neutral Mimics).
- **`Awareness` buff**: every item heap's 3×3 neighbourhood added to `heroMindFov` (reveals item locations through walls).
- **`TalismanOfForesight`** trackers: tracked chars' and heaps' 3×3 neighbourhoods added (cross-level heap tracking checks `depth`/`branch` match).
- **`RevealedArea`** buffs (from scrolls/spells): 3×3 neighbourhood per buff added.
- **Ward/Lotus/SpiritHawk-ally/PowerOfMany-buffed mobs**: each such mob's *own* full FOV (computed recursively via `updateFieldOfView` on that mob) is OR'd into `heroMindFov` — i.e. the hero "sees through" these allies' eyes.
- After all of the above, `mindVisionEnemies` (the list driving the "?" mob icons on minimap/HUD for mobs sensed-but-not-seen) = mobs whose position is in `heroMindFov` but NOT in the true `fieldOfView`.
- Finally `heroMindFov` is OR'd into `fieldOfView` — so anything mind-sensed counts as "visible" for purposes of e.g. targeting checks downstream, though rendering may distinguish (dimmer icon) — that distinction lives in UI code, not `Level`.

## Special FOV additions
- **`SpiritHawk.HawkAlly` with hero `EAGLE_EYE` talent ≥3**: for any mob within `range = 1+(points-2)` of the hawk that isn't already visible, reveal its 3×3 neighbourhood directly into `fieldOfView` (not just mind-fov) — lets the hawk "spot" nearby hidden enemies as true vision.

## Item-heap "seen" flag
- For the hero only, any heap whose `pos` is now in `fieldOfView` and not yet `seen` gets `heap.seen = true`. This is a one-way latch used for "first discovered" bookkeeping (loot notifications etc.), independent of fog-of-war.

## Visited / mapped / fog-of-war (`Dungeon.observe`)
- `Dungeon.observe()` (no-arg) computes `dist = max(hero.viewDistance, 8) * (1 + 0.25*FARSIGHT)`, raised further to `MagicalSight.DISTANCE` if active, then calls `observe(dist+1)`.
- `observe(dist)`:
  1. `level.updateFieldOfView(hero, level.heroFOV)` — recompute true hero FOV (as above).
  2. OR `heroFOV` into `level.visited[]` over a bounding box of `±dist` around the hero (this is the **permanent fog-of-war reveal** — once `visited`, a tile's last-seen terrain stays drawn even when out of current FOV).
  3. Always mark the hero's own 3×3 neighbourhood `visited` regardless of FOV (so you always "remember" tiles you're standing next to).
  4. `GameScene.updateFog(...)` — pushes fog-alpha updates to the renderer for the affected bounding box.
  5. If `MindVision`/`DivineSense` active: also OR each mob's `heroFOV` 3×3 neighbourhood into `visited` (mind-sensed mobs' surroundings get permanently mapped too).
- `level.mapped[]` is a separate, level-generation-time array (e.g. fully-revealed levels, magic mapping scrolls) — distinct from `visited` (player has actually seen it) vs `mapped` (revealed via magic without FOV).
- `Level.cleanWalls()` precomputes `discoverable[]` (see "sense radius" above) — called once during level build, not per-tick.

## Effects/Blobs interacting with FOV
- **`SmokeScreen`**: adds LOS-blocking to affected cells for non-ally/non-Geomancer viewers (see above) — temporary fog cloud.
- **`Light` buff**: raises `viewDistance` to at least 6 (`Light.DISTANCE`) while active; reverts to level default on detach.
- **`Blindness`** / **`Shadows`**: zero out FOV entirely (see "Blindness" above); `Shadows extends Invisibility` (enemy darkness aura effect, e.g. from certain mobs/levels).
- **`Challenges.DARKNESS`**: sets base `level.viewDistance = 2` for the whole run.
- **`WandOfRegrowth`** lotus / **`WandOfWarding`** ward: these summon "mobs" with their own `viewDistance` (1, then ramped) whose FOV feeds `GameScene.updateFog` directly and into hero's `heroMindFov` as described.

## Summary of porting status for this project
- Core shadowcast algorithm + rounding table: **already ported faithfully** (`backend/app/engine/mechanics/shadowcaster.py`).
- Terrain LOS-blocking table + door open/close toggling: appears implemented (`floor.flags.los_blocking`, `TileType.OPEN_DOOR`).
- Warden high-grass exception: implemented in `_effective_blocking`.
- **Not yet ported / verify**: distance-2 corner-fill special case in Python port (check `ROUNDING[2][2] = 2` override is applied — it is, in `_scan_octant`); SoiledFist/GnollGeomancer grass exception; SmokeScreen LOS-blocking addition; Blindness/Shadows full-FOV-blank; discoverable/"sense" fallback radius for blind hero; MindVision/Awareness/DivineSense mob-reveal layer; `Light` buff view-distance floor; per-level `viewDistance` overrides (Halls scaling, boss levels, DARKNESS challenge); heap `seen` latch.
