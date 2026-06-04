# AGENTS.md

## Dev environment

Everything runs in Docker Compose:
```sh
docker compose up --build
```
- Backend: `http://localhost:8080` (FastAPI + uvicorn)
- Frontend: `http://localhost:3000` (nginx serving Vite build, proxies API to backend)
- Frontend dev server: `http://localhost:5173` (HMR, runs via `npm run dev` in frontend/)

## Commands

| Action | Command |
|--------|---------|
| Run all backend tests | `docker compose exec -T backend python3 -m pytest tests/ -v` |
| Run one test | `docker compose exec -T backend python3 -m pytest tests/test_vision.py -v` |
| Run a standalone verify script | `docker compose exec -T backend python3 tests/verify_ranged_combat.py` |
| Frontend lint | `npm run lint` (inside frontend/) |
| Frontend build | `npm run build` (inside frontend/) |

Tests need `PYTHONPATH` to include project root — this is set in the Dockerfile (`ENV PYTHONPATH=/app`). When running tests outside Docker, use `PYTHONPATH=$PYTHONPATH:$(pwd) pytest tests/`.

## Architecture

- **Server-authoritative** — all game state lives on the server (`GameInstance`). Frontend is a pure renderer.
- **WebSocket messages carry full state snapshots** (not deltas). Two message types: `INIT` (full grid/depth, sent on join + floor change) and `STATE_UPDATE` (entities, visible tiles, traps, events).
- **Game loop** at 20 Hz (`asyncio.sleep(0.05)` in `global_game_loop()`). Movement is paced server-side via `update_tick()` with `AUTO_MOVE_INTERVAL = 0.15s`.
- **50 floors**, bosses every 5. First 4 floors use sewers generation (`engine/dungeon/sewers_generation.py`).
- **Vision**: recursive shadowcasting (`engine/mechanics/shadowcaster.py`), ported from SPD. LOS never penetrates solid walls.
- **Players get 60s reconnect grace** (`DISCONNECT_GRACE_SECONDS`). Disconnected heroes stop moving and are reaped after the window.

## Key code locations

| Component | Path |
|-----------|------|
| FastAPI entry + WS handler | `backend/app/main.py` |
| Central game loop + state | `backend/app/engine/manager.py` |
| Dungeon generation (sewers) | `backend/app/engine/dungeon/` |
| Entity classes | `backend/app/engine/entities/base.py` |
| Mob definitions | `backend/app/engine/entities/mobs.py` |
| Combat/CV/AI systems | `backend/app/engine/systems/` |
| Frontend entry + game loop | `frontend/src/App.jsx` |
| Tile rendering | `frontend/src/rendering/sewers/draw.js` |
| Debug API | `frontend/src/dev/useDebugApi.js` |

## Debugging (frontend)

Dev build exposes `window.__debug`. In Chrome DevTools, run:
- `__debug.ascii()` — ASCII map with entities
- `__debug.at(x, y)` — tile info at cell
- `__debug.entities()`, `__debug.vision()`, `__debug.camera()`, `__debug.me()`, `__debug.depth()`
- `__debug.help()` — full list

Prefer `evaluate_script` over screenshots for structured data.

## Implementation rules

- **Reference original SPD** at `../shattered-pixel-dungeon` for game rules, map generation, and mechanics. Implement based on that codebase, not guesswork.
- Game state is **never** client-authoritative. Movement, combat, item usage all go through server dispatch.
- `WAIT` message is intentionally a no-op (no turn-based mechanic in real-time engine).
- When adding mobs/items, register them in `mobs.py`/`base.py` imports in `manager.py`.

## Found conventions

- Python: no typechecker, no formatter config found. Bare `requirements.txt` (no pyproject.toml).
- JavaScript (React): Vite 8 beta, ESLint with `eslint-plugin-react-hooks` and `react-refresh`. No TypeScript. No JS tests.
- Tests use `pytest` with a `GameInstance("test-game")` pattern — spawn in-process, no Docker needed when PYTHONPATH is set.
- Naming: `snake_case` in Python, `PascalCase` for components, `camelCase` for JS functions/vars.
