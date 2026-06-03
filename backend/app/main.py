import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List, Dict
import asyncio
import json
import uuid
import os
from app.engine.manager import GameInstance
from app.engine.entities.base import Position

app = FastAPI(title="Online Pixel Dungeon API")

class ConnectionManager:
    def __init__(self):
        # game_id -> {websocket: player_id}
        self.active_connections: Dict[str, Dict[WebSocket, str]] = {}
        self.game_instances: Dict[str, GameInstance] = {}
        self.last_sent_floor: Dict[str, Dict[str, int]] = {}

    async def connect(self, game_id: str, websocket: WebSocket, player_id: str):
        await websocket.accept()
        if game_id not in self.active_connections:
            self.active_connections[game_id] = {}
            self.game_instances[game_id] = GameInstance(game_id)
            self.last_sent_floor[game_id] = {}

        self.active_connections[game_id][websocket] = player_id

    async def send_player_init(self, game_id: str, websocket: WebSocket, player_id: str):
        game = self.game_instances[game_id]
        state = game.get_state(player_id)
        player_floor = state.get("depth", 1)

        await websocket.send_json({
            "type": "INIT",
            "player_id": player_id,
            "depth": player_floor,
            "grid": state["grid"],
            "width": game.width,
            "height": game.height,
            "traps": state.get("traps", []),
        })
        self.last_sent_floor.setdefault(game_id, {})[player_id] = player_floor


    def disconnect(self, game_id: str, websocket: WebSocket):
        if game_id in self.active_connections:
            if websocket in self.active_connections[game_id]:
                player_id = self.active_connections[game_id][websocket]
                del self.active_connections[game_id][websocket]
                if game_id in self.last_sent_floor:
                    self.last_sent_floor[game_id].pop(player_id, None)
            if not self.active_connections[game_id]:
                del self.active_connections[game_id]
                self.last_sent_floor.pop(game_id, None)

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
                            "width": game.width,
                            "height": game.height,
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
async def game_websocket(websocket: WebSocket, game_id: str, class_type: str = "warrior", difficulty: str = "normal", name: str = None, admin_secret: str = ""):
    player_id = str(uuid.uuid4())
    await manager.connect(game_id, websocket, player_id)

    game = manager.game_instances[game_id]
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
        manager.disconnect(game_id, websocket)
        if player_id in game.players:
            del game.players[player_id]

async def global_game_loop():
    while True:
        for game_id in list(manager.active_connections.keys()):
            await manager.broadcast_state(game_id)
        await asyncio.sleep(0.05)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(global_game_loop())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
