"""Generic area-effect system analogous to SPD's Blob class.

Each BlobArea occupies a set of cells and applies per-tick effects to entities
standing within it. Primarily used for foliage (grants Shadows/invisibility)
and future gas/fire/water areas.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from app.engine.entities.base import Entity
from app.engine.game.floor_state import FloorState


def tick_foliage_blobs(floors: Dict[int, FloorState], players: Dict[str, Entity]) -> List[dict]:
    """Tick all foliage blob areas: grant Shadows buff to players standing in them."""
    events: List[dict] = []

    for floor in floors.values():
        for blob_id, blob in list(floor.blob_areas.items()):
            if blob.get("type") != "foliage":
                continue

            cells: Set[Tuple[int, int]] = set(tuple(c) for c in blob.get("cells", []))

            # Grant Shadows buff to players in foliage cells
            for player in players.values():
                if player.floor_id != floor.floor_id:
                    continue
                if not player.is_alive:
                    continue
                pos = (player.pos.x, player.pos.y)
                if pos in cells:
                    player.add_buff("shadows", duration=2.0, stack_mode="extend")

            # Tick remaining duration if finite
            remaining = blob.get("remaining", 0.0)
            if remaining > 0:
                remaining -= 0.05  # 20Hz
                blob["remaining"] = remaining
                if remaining <= 0:
                    del floor.blob_areas[blob_id]
                    events.append({
                        "type": "BLOB_DEPLETED",
                        "data": {"blob_id": blob_id, "blob_type": "foliage"},
                    })

    return events
