"""Event queue for GameInstance.

Events are buffered each tick, then filtered per-player (by floor, target, and
line-of-sight to the source) before being flushed to clients.
"""

from typing import List, Optional


class EventsMixin:
    def add_event(self, event_type: str, data: dict = None, floor_id: Optional[int] = None, player_id: Optional[str] = None, source_player_id: Optional[str] = None):
        event = {
            "type": event_type,
            "data": data or {},
        }
        if floor_id is not None:
            event["_floor_id"] = floor_id
        if player_id is not None:
            event["_player_id"] = player_id
        if source_player_id is not None:
            event["_source_player_id"] = source_player_id
        self.events.append(event)

    def filter_events_for_player(self, events: List[dict], player_id: str) -> List[dict]:
        player = self.players.get(player_id)
        if not player:
            return []

        filtered = []
        for event in events:
            event_player = event.get("_player_id")
            event_floor = event.get("_floor_id")
            source_player_id = event.get("_source_player_id")

            if event_player is not None and event_player != player_id:
                continue

            if event_floor is not None and event_floor != player.floor_id:
                continue

            # LOS check: events tagged with source_player_id are only audible/visible
            # to players who can see that source player
            if source_player_id is not None and source_player_id != player_id:
                source_player = self.players.get(source_player_id)
                if source_player and source_player.floor_id == player.floor_id:
                    if not self._is_in_los(player.pos, source_player.pos, floor_id=player.floor_id):
                        continue

            filtered.append({k: v for k, v in event.items() if not k.startswith("_")})

        return filtered

    def flush_events(self):
        events = self.events
        self.events = []
        return events
