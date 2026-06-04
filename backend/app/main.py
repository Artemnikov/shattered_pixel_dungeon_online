import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List, Dict, Tuple
import asyncio
import json
import time
import uuid
import os
from app.engine.manager import GameInstance
from app.engine.entities.base import Position

app = FastAPI(title="Online Pixel Dungeon API")

# How long a disconnected player's hero is kept alive in the world so the client
# can reconnect (same session) and resume the same run. After this, the reaper
# removes the orphaned player.
DISCONNECT_GRACE_SECONDS = 60.0

class ConnectionManager:
    def __init__(self):
        # game_id -> {websocket: player_id}
        self.active_connections: Dict[str, Dict[WebSocket, str]] = {}
        self.game_instances: Dict[str, GameInstance] = {}
        self.last_sent_floor: Dict[str, Dict[str, int]] = {}
        # game_id -> {session_id: player_id} — stable identity across reconnects.
        self.sessions: Dict[str, Dict[str, str]] = {}
        # game_id -> {player_id: monotonic deadline} — players awaiting reconnect.
        self.disconnect_deadline: Dict[str, Dict[str, float]] = {}

    async def connect(self, game_id: str, websocket: WebSocket, session_id: str) -> Tuple[str, bool]:
        """Accept a connection and resolve its player identity.

        Returns (player_id, is_new). When the session already maps to a player
        still present in the game, we rebind to that existing hero (preserving
        inventory/HP/depth/position) instead of spawning a fresh one.
        """
        await websocket.accept()
        if game_id not in self.active_connections:
            self.active_connections[game_id] = {}
            self.game_instances[game_id] = GameInstance(game_id)
            self.last_sent_floor[game_id] = {}
            self.sessions[game_id] = {}
            self.disconnect_deadline[game_id] = {}

        game = self.game_instances[game_id]
        existing_player_id = self.sessions[game_id].get(session_id)
        if existing_player_id and existing_player_id in game.players:
            # Reconnect: rebind to the live hero and cancel its removal.
            player_id = existing_player_id
            self.disconnect_deadline[game_id].pop(player_id, None)
            # Force a fresh INIT (full grid/depth) on the next broadcast.
            self.last_sent_floor[game_id].pop(player_id, None)
            self.active_connections[game_id][websocket] = player_id
            return player_id, False

        player_id = str(uuid.uuid4())
        self.sessions[game_id][session_id] = player_id
        self.active_connections[game_id][websocket] = player_id
        return player_id, True

    async def send_player_init(self, game_id: str, websocket: WebSocket, player_id: str):
        game = self.game_instances[game_id]
        state = game.get_state(player_id)
        player_floor = state.get("depth", 1)

        await websocket.send_json({
            "type": "INIT",
            "player_id": player_id,
            "depth": player_floor,
            "grid": state["grid"],
            "width": state["width"],
            "height": state["height"],
            "traps": state.get("traps", []),
        })
        self.last_sent_floor.setdefault(game_id, {})[player_id] = player_floor


    def disconnect(self, game_id: str, websocket: WebSocket):
        if game_id not in self.active_connections:
            return
        if websocket in self.active_connections[game_id]:
            player_id = self.active_connections[game_id][websocket]
            del self.active_connections[game_id][websocket]
            # Keep the hero in the world during a grace window so the client can
            # reconnect (same session) and resume. The reaper removes it if not.
            game = self.game_instances.get(game_id)
            if game and player_id in game.players:
                player = game.players[player_id]
                # Stop any in-progress walking so a disconnected hero stands still.
                player.move_intent = None
                player.path_queue = []
                self.disconnect_deadline.setdefault(game_id, {})[player_id] = (
                    time.monotonic() + DISCONNECT_GRACE_SECONDS
                )

    def reap_expired_players(self, game_id: str):
        """Remove heroes whose reconnect grace window has elapsed."""
        deadlines = self.disconnect_deadline.get(game_id)
        if not deadlines:
            return
        game = self.game_instances.get(game_id)
        connected = set(self.active_connections.get(game_id, {}).values())
        now = time.monotonic()
        for player_id, deadline in list(deadlines.items()):
            if player_id in connected:
                # Reconnected since the deadline was set; clear it.
                deadlines.pop(player_id, None)
                continue
            if now < deadline:
                continue
            deadlines.pop(player_id, None)
            self.last_sent_floor.get(game_id, {}).pop(player_id, None)
            if game and player_id in game.players:
                del game.players[player_id]
            sessions = self.sessions.get(game_id, {})
            for sid, pid in list(sessions.items()):
                if pid == player_id:
                    del sessions[sid]

    def cleanup_if_empty(self, game_id: str):
        """Tear down a game once nobody is connected and no hero awaits reconnect."""
        if self.active_connections.get(game_id):
            return
        if self.disconnect_deadline.get(game_id):
            return
        game = self.game_instances.get(game_id)
        if game and game.players:
            return
        self.active_connections.pop(game_id, None)
        self.game_instances.pop(game_id, None)
        self.last_sent_floor.pop(game_id, None)
        self.sessions.pop(game_id, None)
        self.disconnect_deadline.pop(game_id, None)

    async def broadcast_state(self, game_id: str):
        if game_id in self.active_connections and game_id in self.game_instances:
            game = self.game_instances[game_id]
            game.update_tick()
            events = game.flush_events()
            
            for connection, player_id in self.active_connections[game_id].items():
                try:
                    if player_id not in game.players:
                        continue

                    state = game.get_state(player_id)
                    player_floor = state.get("depth", 1)
                    previous_floor = self.last_sent_floor.setdefault(game_id, {}).get(player_id)
                    
                    if previous_floor != player_floor:
                        await connection.send_json({
                            "type": "INIT",
                            "depth": player_floor,
                            "grid": state["grid"],
                            "width": state["width"],
                            "height": state["height"],
                            "traps": state.get("traps", []),
                        })
                        self.last_sent_floor[game_id][player_id] = player_floor
                    
                    player_obj = game.players.get(player_id)
                    gold = player_obj.gold if player_obj else 0
                    energy = player_obj.energy if player_obj else 0

                    await connection.send_json({
                        "type": "STATE_UPDATE",
                        "depth": player_floor,
                        "difficulty": game.difficulty,
                        "players": state["players"],
                        "mobs": state["mobs"],
                        "items": state.get("items", []),
                        "visible_tiles": state.get("visible_tiles", []),
                        "traps": state.get("traps", []),
                        "gold": gold,
                        "energy": energy,
                        "events": game.filter_events_for_player(events, player_id)
                    })
                except Exception as e:
                    print(f"Error broadcasting to {player_id}: {e}")
                    pass

manager = ConnectionManager()

@app.get("/")
async def root():
    return {"message": "Online Pixel Dungeon Server is running"}

@app.websocket("/ws/game/{game_id}")
async def game_websocket(websocket: WebSocket, game_id: str, class_type: str = "warrior", difficulty: str = "normal", name: str = None, admin_secret: str = "", session: str = None):
    session_id = session or str(uuid.uuid4())
    player_id, is_new = await manager.connect(game_id, websocket, session_id)

    game = manager.game_instances[game_id]
    if is_new:
        if game.player_count == 0: # First player sets difficulty
            game.change_difficulty(difficulty)

        is_admin = bool(admin_secret and admin_secret == os.environ.get("ADMIN_SECRET", "admin"))
        player_name = "admin" if is_admin else (name.strip()[:20] if name and name.strip() else f"Player_{player_id[:4]}")
        game.add_player(player_id, player_name, class_type, is_admin=is_admin)
    await manager.send_player_init(game_id, websocket, player_id)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message["type"] == "PING":
                await websocket.send_json({"type": "PONG"})
                continue

            if message["type"] == "MOVE":
                direction = message["direction"]
                dx, dy = 0, 0
                if direction == "UP": dy = -1
                elif direction == "DOWN": dy = 1
                elif direction == "LEFT": dx = -1
                elif direction == "RIGHT": dx = 1
                elif direction == "UP_LEFT": dx = -1; dy = -1
                elif direction == "UP_RIGHT": dx = 1; dy = -1
                elif direction == "DOWN_LEFT": dx = -1; dy = 1
                elif direction == "DOWN_RIGHT": dx = 1; dy = 1
                if player_id in game.players:
                    # A single tap-step overrides any held keyboard intent / travel path.
                    game.players[player_id].path_queue = []
                    game.players[player_id].move_intent = None
                game.move_entity(player_id, dx, dy)

            elif message["type"] == "MOVE_INTENT":
                # Held keyboard direction. The update tick paces the actual stepping
                # (see GameInstance.update_tick), so movement speed is server-authoritative.
                game.set_move_intent(player_id, int(message.get("dx", 0)), int(message.get("dy", 0)))

            elif message["type"] == "MOVE_STOP":
                game.set_move_intent(player_id, 0, 0)

            elif message["type"] == "MOVE_TO":
                tx, ty = message.get("x"), message.get("y")
                if tx is not None and ty is not None and player_id in game.players:
                    player = game.players[player_id]
                    player.move_intent = None
                    path = game._bfs_full_path(player.pos, Position(x=tx, y=ty), player.floor_id)
                    player.path_queue = list(path)
                    player.last_auto_move_time = 0.0

            elif message["type"] == "EXECUTE_ITEM_ACTION":
                # Generic SPD-style dispatch: {item_id, action, target_x?, target_y?}.
                game.execute_item_action(
                    player_id, message["item_id"], message["action"],
                    message.get("target_x"), message.get("target_y"),
                )

            elif message["type"] == "SET_QUICKSLOT":
                game.set_quickslot(player_id, message["index"], message["item_id"])

            elif message["type"] == "USE_QUICKSLOT":
                game.use_quickslot(
                    player_id, message["index"],
                    message.get("target_x"), message.get("target_y"),
                )

            # --- legacy handlers (thin wrappers over the generic dispatch) ---
            elif message["type"] == "EQUIP_ITEM":
                game.execute_item_action(player_id, message["item_id"], "EQUIP")

            elif message["type"] == "DROP_ITEM":
                game.execute_item_action(player_id, message["item_id"], "DROP")

            elif message["type"] == "USE_ITEM":
                game.use_item(player_id, message["item_id"])

            elif message["type"] == "CHANGE_DIFFICULTY":
                new_difficulty = message["difficulty"]
                game.change_difficulty(new_difficulty)

            elif message["type"] == "RANGED_ATTACK":
                game.perform_ranged_attack(
                    player_id, message["item_id"], message["target_x"], message["target_y"],
                )

            elif message["type"] == "SEARCH":
                game.search(player_id)

            elif message["type"] == "WAIT":
                # WAIT no longer triggers a reveal. The reveal/search action is now
                # exclusively the examine-mode flow on the magnifying-glass button, so
                # tapping your own character (which sends WAIT) must not search. There
                # is no turn-based wait mechanic in this real-time engine yet, so this
                # is intentionally a no-op.
                pass

    except WebSocketDisconnect:
        # Keep the hero alive for the reconnect grace window (see reaper); the
        # player is only removed once the deadline elapses without a reconnect.
        manager.disconnect(game_id, websocket)

async def global_game_loop():
    while True:
        for game_id in list(manager.game_instances.keys()):
            manager.reap_expired_players(game_id)
            await manager.broadcast_state(game_id)
            manager.cleanup_if_empty(game_id)
        await asyncio.sleep(0.05)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(global_game_loop())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
