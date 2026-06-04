"""World interaction for GameInstance: searching, locked doors, and traps.

Reveals hidden doors/traps around a searching player, consumes keys to open
locked doors, and resolves trap triggers when a player steps onto one.
"""

from typing import List

from app.engine.dungeon.generator import TileType
from app.engine.entities.base import Key, Player
from app.engine.game.floor_state import FloorState


class WorldInteractionMixin:
    def search(self, player_id: str):
        player = self.players.get(player_id)
        if not player:
            return

        floor = self._get_or_create_floor(player.floor_id)
        patches: List[dict] = []
        # Every in-bounds cell scanned this search, so the client can sweep a
        # CheckedCell ring over the whole radius (mirrors the original drawing a
        # CheckedCell on each cell in range, not only the ones that revealed something).
        checked: List[List[int]] = []
        found_secret = False

        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                tx = player.pos.x + dx
                ty = player.pos.y + dy
                if not (0 <= tx < floor.width and 0 <= ty < floor.height):
                    continue

                checked.append([tx, ty])
                pos = (tx, ty)
                if pos in floor.hidden_doors:
                    actual_tile = floor.hidden_doors.pop(pos)
                    floor.grid[ty][tx] = actual_tile
                    patches.append({"x": tx, "y": ty, "tile": actual_tile})
                    found_secret = True

                trap = floor.traps.get(pos)
                if trap and trap.hidden:
                    trap.hidden = False
                    found_secret = True
                    if floor.grid[ty][tx] == TileType.SECRET_TRAP:
                        floor.grid[ty][tx] = TileType.TRAP
                        patches.append({"x": tx, "y": ty, "tile": TileType.TRAP})

        if patches:
            # Tile mutations changed the grid — refresh derived flag maps
            # so LOS / pathfinding / openSpace pick up the new state on
            # the next query (a revealed door is now passable + see-through).
            floor.rebuild_flags()
            self.add_event("MAP_PATCH", {"tiles": patches}, floor_id=player.floor_id)

        # Original plays the SECRET sound whenever a door OR a trap is revealed.
        if found_secret:
            self.add_event("PLAY_SOUND", {"sound": "SECRET"}, player_id=player_id)

        # Searcher-only: drives the operate (hand-raise) animation + the cyan ring
        # sweep on the searching client. x/y is the hero position the rings emanate from.
        self.add_event(
            "SEARCH",
            {
                "player": player_id,
                "x": player.pos.x,
                "y": player.pos.y,
                "cells": checked,
                "revealed_tiles": len(patches),
            },
            player_id=player_id,
        )

    def _try_unlock_locked_door(self, player: Player, floor: FloorState, x: int, y: int) -> bool:
        key_id = floor.locked_doors.get((x, y))
        if not key_id:
            return False

        key_idx = next(
            (
                idx
                for idx, item in enumerate(player.inventory)
                if isinstance(item, Key) and item.key_id == key_id
            ),
            -1,
        )
        if key_idx == -1:
            return False

        player.inventory.pop(key_idx)
        floor.locked_doors.pop((x, y), None)
        floor.grid[y][x] = TileType.DOOR
        # Tile mutated from LOCKED_DOOR to DOOR — refresh flag maps so
        # LOS/pathfinding sees the door as passable now.
        floor.rebuild_flags()

        self.add_event("MAP_PATCH", {"tiles": [{"x": x, "y": y, "tile": TileType.DOOR}]}, floor_id=player.floor_id)
        self.add_event("UNLOCK", {"player": player.id, "x": x, "y": y}, floor_id=player.floor_id)
        return True

    def _trigger_trap_if_needed(self, floor: FloorState, player: Player, floor_id: int):
        pos = (player.pos.x, player.pos.y)
        trap = floor.traps.get(pos)
        if not trap or not trap.active:
            return

        patches: List[dict] = []
        if trap.hidden:
            trap.hidden = False

        # Any trap tile -> INACTIVE_TRAP on trigger
        tile = floor.grid[player.pos.y][player.pos.x]
        if tile in (TileType.SECRET_TRAP, TileType.TRAP):
            floor.grid[player.pos.y][player.pos.x] = TileType.INACTIVE_TRAP
            patches.append({"x": player.pos.x, "y": player.pos.y, "tile": TileType.INACTIVE_TRAP})

        trap.active = False

        damage = 2
        dealt = player.take_damage(damage)

        if patches:
            self.add_event("MAP_PATCH", {"tiles": patches}, floor_id=floor_id)

        self.add_event(
            "TRAP_TRIGGERED",
            {"player": player.id, "trap": trap.trap_type, "damage": dealt},
            floor_id=floor_id,
        )
        if dealt > 0:
            self.add_event("DAMAGE", {"target": player.id, "amount": dealt}, floor_id=floor_id)
            self.add_event("PLAY_SOUND", {"sound": "HIT_BODY"}, floor_id=floor_id, source_player_id=player.id)
            if player.hp / max(1, player.get_total_max_hp()) <= 0.3:
                self.add_event("PLAY_SOUND", {"sound": "HEALTH_WARN"}, player_id=player.id)
