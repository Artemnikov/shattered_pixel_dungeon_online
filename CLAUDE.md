# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Important
This project is a remake of the original shattered pixel dungeon game.
Before implementing anything, find the exact flow rules from the original project at `../shattered-pixel-dungeon` and implement based on the original game rules logic and map building.

## Commands

### Backend (run from `backend/`)
```bash
# Run server (dev)
venv/bin/python app/main.py          # port 8080

# Run all tests
venv/bin/python -m pytest tests/

# Run a single test file
venv/bin/python -m pytest tests/test_combat.py

# Run a single test
venv/bin/python -m pytest tests/test_combat.py::test_name

# Export TypeScript contract schema (used by frontend gen:types)
venv/bin/python scripts/export_contract_schema.py
```

### Frontend (run from `frontend/`)
```bash
npm run dev          # Vite dev server — http://localhost:5173
npm run build
npm run lint
npm run typecheck
npm run gen:types    # regenerate entity types from backend Pydantic schemas
```

### Docker
```bash
docker build -t opd-backend backend/
docker run -p 8080:8080 opd-backend
```

## Architecture

Real-time multiplayer dungeon crawler. Client-server over WebSockets. Game loop runs at 20 Hz (`asyncio.sleep(0.05)` in `main.py::global_game_loop`).

### Backend (`backend/app/`)

**Entry / connection layer**
- `main.py` — FastAPI app; `ConnectionManager` owns WebSocket connections, session→player mapping, reconnect grace window (60s), and broadcasts per-tick state snapshots
- WebSocket: `ws://host/ws/game/{game_id}?class_type=&difficulty=&name=&session=&seed=`
- REST: `GET /api/talents/{class_type}` — talent tree for character selection

**`engine/manager.py` — `GameInstance`**  
Central game state for one multiplayer session. Built from composable mixins (each in `engine/game/`):
- `TickMixin` — drives every subsystem each tick (death, buffs, auto-move, regen, mob AI, respawn)
- `MovementCombatMixin` — move/attack resolution, BFS pathfinding
- `GenerationMixin` — creates `FloorState` objects on demand; floors 1-4 use SPD-faithful levelgen (`spd_levelgen/`), floor 5 is boss level
- `SerializationMixin` — builds per-player JSON snapshot; scrambles unidentified potion/scroll names per-run
- `VisionMixin` — shadowcasting LOS (`engine/mechanics/shadowcaster.py`)
- `EventsMixin` — queues combat/audio events; `filter_events_for_player` culls by visibility
- Other mixins: `FloorAccessMixin`, `PlayersMixin`, `WorldInteractionMixin`, `ItemsMixin`, `TalentsMixin`, `RogueMixin`, `ArmorAbilitiesMixin`

**`engine/dungeon/`**
- `spd_levelgen/` — faithful port of SPD's Java levelgen pipeline: `SpdRandom` (48-bit LCG, byte-identical to `java.util.Random`), `RegularLevel`, `BossLevel`, room graph, builders, painters, mob spawner, trap/item placement
- `terrain_flags.py` — bitmask flag maps (passable, solid, open, etc.) built once per floor and cached on `FloorState.flags`
- `generator.py` — `TileType` enum, `TrapInfo`

**`engine/entities/`**
- `base.py` — `Entity`, `Player`, `Mob`, `Item`, `Weapon`, `Potion`, `Bag`, `Position`, `CharacterClass`, `Difficulty`, `Effect`, `Faction`
- `mobs.py` — all mob types (`Rat`, `Goo`, `Crab`, `Slime`, ...)
- `buffs.py` — buff/debuff processing
- `subclasses.py` — subclass definitions, talent trees (`TALENT_DEFS`, `TALENT_TITLES`, etc.)
- `item_actions.py` — SPD-style item action dispatch (EQUIP, DROP, USE, THROW, ...)

**`engine/game/constants.py`** — canonical game constants (floor ranges, tick intervals, map sizes). Import from here, not from `manager.py`.

**`app/schemas/`** — Pydantic WebSocket envelopes:
- Outbound: `InitMessage` (grid on connect/floor change), `StateUpdateMessage` (every tick), `PongMessage`
- Inbound: `CLIENT_MESSAGE_ADAPTER` dispatches to typed message models in `messages.py`

### Frontend (`frontend/src/`)
- `App.jsx` — canvas game loop, WebSocket client, input handling
- `rendering/sewers/draw.js` — tile/sprite rendering (32×32 tiles, 2× scale)
- `audio/AudioManager.js` — music and SFX
- `types/generated/entities.ts` — auto-generated from backend schemas via `gen:types`; do not edit manually

**Assets** (`frontend/src/assets/pixel-dungeon/`) — SPD sprite sheets, tilesets, audio.

## Key Patterns

- Game state lives entirely on the server; frontend is a pure renderer — never put game logic in the frontend
- Floors are lazy-generated on first visit; `FloorState` holds the full per-floor runtime state (grid, mobs, items, doors, traps, flag maps)
- `SpdRandom` must stay byte-identical to Java's `java.util.Random` — any change breaks deterministic seed replay
- `kind_appearance` in `SerializationMixin` maps potion/scroll kinds to per-run scrambled labels + sprite columns; mirrors `ItemSpriteSheet.java`
- Factions control friendly-fire; `effect` enum drives status icons
- `SEWERS_MAX_FLOOR = 4`, `PRISON_MAX_FLOOR = 9`, `MAX_FLOOR_ID = 50`; boss floors are 5, 10, 15, …

## Debugging Tile Rendering / Map Analysis

Dev build exposes `window.__debug` (see `frontend/src/dev/useDebugApi.js`). When investigating rendering, vision, or map bugs, use `mcp__chrome-devtools` to navigate to `http://localhost:5173`, start a game, then `evaluate_script` against the page:

- `__debug.ascii()` — ASCII map with entities overlaid
- `__debug.at(x, y)` — tile id/name + entities at cell + visibility/door state
- `__debug.entities()` — players + mobs with positions
- `__debug.vision()`, `__debug.camera()`, `__debug.me()`, `__debug.depth()`, `__debug.bounds()`
- `__debug.help()` — list all

Prefer `evaluate_script` over `take_screenshot` — cheaper and gives structured data. Screenshot only when the data looks correct but visuals look wrong.