import asyncio

from app.main import ConnectionManager


class DummyWebSocket:
    def __init__(self):
        self.accepted = False
        self.messages = []

    async def accept(self):
        self.accepted = True

    async def send_json(self, payload):
        self.messages.append(payload)


def test_init_uses_player_floor_even_if_game_depth_differs():
    async def scenario():
        manager = ConnectionManager()
        websocket = DummyWebSocket()
        game_id = "test-game"
        player_id = "test-player"

        await manager.connect(game_id, websocket, player_id)
        assert websocket.accepted is True
        assert websocket.messages == []

        game = manager.game_instances[game_id]
        game.generate_floor(7)
        assert game.depth == 7

        game.add_player(player_id, "Player_test")
        await manager.send_player_init(game_id, websocket, player_id)

        init_payload = websocket.messages[-1]
        assert init_payload["type"] == "INIT"
        assert init_payload["player_id"] == player_id
        assert init_payload["depth"] == 1
        assert init_payload["grid"] == game._get_or_create_floor(1).grid
        assert manager.last_sent_floor[game_id][player_id] == (1, 0)

    asyncio.run(scenario())
