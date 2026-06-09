# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
npm run dev          # Vite dev server — http://localhost:5173
npm run build
npm run lint
npm run typecheck
npm run gen:types    # regenerate entity types from backend Pydantic schemas
```

`gen:types` runs `export_contract_schema.py` in the backend venv, then `json2ts` to emit `src/types/generated/entities.ts`. Never edit that file manually.

## Architecture

**Pure renderer.** All game logic lives on the server. The frontend only renders state and sends player input.

### Screen flow (`App.jsx`)
Three states: `WELCOME → SELECT → PLAYING`. `App.jsx` is the monolith that owns all React state; it wires together the hooks below and renders the HUD.

### Key hooks
| Hook | File | Purpose |
|---|---|---|
| `useGameSocket` | `net/useGameSocket.ts` | WebSocket lifecycle, reconnect/heartbeat, state hydration from server messages |
| `useGameRenderer` | `rendering/useGameRenderer.js` | `requestAnimationFrame` loop driving canvas draw each frame |
| `useCanvasControls` | `input/useCanvasControls.js` | Pan/zoom/pinch, tap dispatch (targeting, examine) |
| `useKeyboardControls` | `input/useKeyboardControls.js` | Keyboard shortcuts |
| `useAssetImages` | `rendering/useAssetImages.js` | Loads sprite sheets; returns `assetImages` used by the renderer |
| `useMusicByDepth` | `audio/useMusicByDepth.js` | Switches background music track based on depth/boss state |

### Rendering pipeline (`rendering/`)
`useGameRenderer` calls these in order each frame:
1. `sewers/draw.js` — water background + animated water texture
2. `draw/grid.js` — terrain tiles (base layer)
3. `draw/terrainFeatures.js` — doors, traps, chests
4. `draw/items.js` — floor items
5. `draw/mobs.js` / `draw/players.js` — entities with lerp animation
6. `draw/projectiles.js`, `draw/particles.js`, `draw/searchEffects.js`, `draw/warnedTiles.js`, `draw/floatingText.js` — effects

**Tile rendering** uses per-region atlases. `rendering/regions.js::regionForDepth` maps depth → region name (sewers/prison/caves/city/halls), matching SPD's 5-floor-per-region layout. `rendering/sewers/terrainMapper.js` and `wallMapper.js` translate tile IDs to atlas rects (quadrant-based, matching SPD's `SewerLevel` tile sheet layout).

**Mob/player sprites** — frame sizes are defined in `rendering/mobs.js`. Non-standard sizes (Gnoll: 12×15, Snake: 12×11, etc.) must match the original SPD sprite class definitions.

**Item sprites** — `rendering/sprites.js::ITEM_SPRITES` maps name substrings to `[col, row]` in `items.png`. Coordinates are ported from `ItemSpriteSheet.java`; more-specific keys must appear before generic ones (e.g. `"Scroll Holder"` before `"Scroll"`).

### Animation model
Entities have `renderPos` (interpolated) and `targetPos` (server position). Movement is client-side lerp over `MOVE_DURATION` ms. Attack animation timing mirrors SPD (`PLAYER_ATTACK_DURATION`, `HIT_CONNECT_DELAY`, `FLASH_DURATION` in `constants.js`).

### Types
- `src/types/contract.ts` — hand-written WS envelope types (do not overwrite)
- `src/types/generated/entities.ts` — auto-generated from backend Pydantic (do not edit)

### WebSocket messages
All outbound messages go through `net/send.ts`. Inbound message handling is in `useGameSocket`. Input actions resolved by `input/resolveTap.js` (tap → `MOVE_TO` / `ATTACK` etc.) and dispatched directly via `socketRef`.

### Targeting / examine flow
`targetingMode` in `App.jsx` drives cursor and tap routing:
- `false` — normal movement taps
- `{ itemId, action }` — waiting for a target cell for THROW/ZAP
- `{ ability }` — armor ability targeting
- `{ prepStrike: true }` — preparation strike
- `string` (item ID) — ranged weapon repeat-fire mode

Examine mode (magnifying glass) is a separate boolean; first trigger arms it, second performs SEARCH — mirrors SPD's two-step.

### Audio
`AudioManager` (singleton, `audio/AudioManager.js`) uses Web Audio API. SFX volume is driven by `menu/menuSettings.js`. Music is managed separately via `useMusicByDepth`.

### Debug API
In dev builds, `window.__debug` is exposed by `dev/useDebugApi.js`. Use `mcp__chrome-devtools__evaluate_script` against `http://localhost:5173` — `__debug.ascii()`, `__debug.at(x,y)`, `__debug.entities()`, etc. See project-root CLAUDE.md for full list.
