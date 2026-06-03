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


def test_reconnect_same_session_rebinds_to_existing_hero():
    async def scenario():
        manager = ConnectionManager()
        game_id, session_id = "g", "sess-1"

        ws1 = DummyWebSocket()
        player_id, is_new = await manager.connect(game_id, ws1, session_id)
        assert is_new is True
        game = manager.game_instances[game_id]
        game.add_player(player_id, "Hero")

        # Mutate state so we can prove it survives the reconnect.
        game.players[player_id].hp = 7
        game.players[player_id].gold = 42

        # Drop: hero is kept alive (grace), not deleted.
        manager.disconnect(game_id, ws1)
        assert player_id in game.players
        assert player_id in manager.disconnect_deadline[game_id]

        # Reconnect with the same session → rebind to the same hero.
        ws2 = DummyWebSocket()
        rejoin_id, is_new2 = await manager.connect(game_id, ws2, session_id)
        assert is_new2 is False
        assert rejoin_id == player_id
        assert game.players[player_id].hp == 7
        assert game.players[player_id].gold == 42
        # Grace deadline cleared; INIT will be re-sent (last_sent_floor reset).
        assert player_id not in manager.disconnect_deadline[game_id]
        assert player_id not in manager.last_sent_floor[game_id]
        assert manager.active_connections[game_id][ws2] == player_id

    asyncio.run(scenario())


def test_new_session_spawns_fresh_hero():
    async def scenario():
        manager = ConnectionManager()
        game_id = "g"

        ws1 = DummyWebSocket()
        pid1, _ = await manager.connect(game_id, ws1, "sess-A")
        manager.game_instances[game_id].add_player(pid1, "A")

        ws2 = DummyWebSocket()
        pid2, is_new = await manager.connect(game_id, ws2, "sess-B")
        assert is_new is True
        assert pid2 != pid1

    asyncio.run(scenario())


def test_reaper_removes_hero_after_grace_expires():
    async def scenario():
        manager = ConnectionManager()
        game_id, session_id = "g", "sess-1"

        ws = DummyWebSocket()
        player_id, _ = await manager.connect(game_id, ws, session_id)
        game = manager.game_instances[game_id]
        game.add_player(player_id, "Hero")

        manager.disconnect(game_id, ws)
        # Force the deadline into the past, then reap.
        manager.disconnect_deadline[game_id][player_id] = 0.0
        manager.reap_expired_players(game_id)

        assert player_id not in game.players
        assert session_id not in manager.sessions[game_id]

        # A subsequent connect with the same session id spawns fresh.
        ws2 = DummyWebSocket()
        new_id, is_new = await manager.connect(game_id, ws2, session_id)
        assert is_new is True
        assert new_id != player_id

    asyncio.run(scenario())


def test_reconnect_before_reap_keeps_hero():
    async def scenario():
        manager = ConnectionManager()
        game_id, session_id = "g", "sess-1"

        ws = DummyWebSocket()
        player_id, _ = await manager.connect(game_id, ws, session_id)
        manager.game_instances[game_id].add_player(player_id, "Hero")

        manager.disconnect(game_id, ws)
        # Reconnect first...
        ws2 = DummyWebSocket()
        await manager.connect(game_id, ws2, session_id)
        # ...then a reaper pass must NOT remove the now-connected hero.
        manager.reap_expired_players(game_id)
        assert player_id in manager.game_instances[game_id].players

    asyncio.run(scenario())
