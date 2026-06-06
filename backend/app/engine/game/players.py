"""Player lifecycle for GameInstance: join, floor traversal, and death.

Handles starting-gear setup per class, stair-based floor changes, and the SPD
death sequence (scatter the backpack, drop a grave).
"""

import random
import uuid
from typing import List, Optional, Tuple

from app.engine.dungeon.generator import TileType
from app.engine.entities.base import (
    Armor,
    Belongings,
    Bow,
    BrokenSeal,
    CharacterClass,
    Dagger,
    Faction,
    Item,
    Player,
    Position,
    QuickSlot,
    ScrollOfRage,
    Staff,
    Stone,
    Weapon,
    WornShortsword,
)
from app.engine.game.constants import MAX_FLOOR_ID
from app.engine.game.floor_state import FloorState


class PlayersMixin:
    def add_player(self, player_id: str, name: str, class_type: str = CharacterClass.WARRIOR, is_admin: bool = False) -> Player:
        floor = self._get_or_create_floor(1)
        spawn_pos = self._get_stairs_pos(TileType.STAIRS_UP, floor_id=floor.floor_id)

        self.player_count += 1

        # Starting gear goes straight into the relevant equip slots (SPD-style:
        # equipped items live in Belongings, not the backpack).
        belongings = Belongings()

        if class_type == CharacterClass.WARRIOR:
            belongings.weapon = WornShortsword(
                id=str(uuid.uuid4()),
            )
            belongings.armor = Armor(
                id=str(uuid.uuid4()),
                name="Cloth Armor",
                tier=1,
                strength_requirement=10,
            )
            belongings.artifact = BrokenSeal(
                id=str(uuid.uuid4()),
            )
            belongings.backpack.collect(Stone(
                id=str(uuid.uuid4()),
                quantity=3,
            ))
            belongings.backpack.collect(ScrollOfRage(
                id=str(uuid.uuid4()),
            ))

        elif class_type == CharacterClass.MAGE:
            belongings.weapon = Staff(
                id=str(uuid.uuid4()),
                name="Mage's Staff",
                damage=2,
                magic_damage=3,
                strength_requirement=10,
                charges=4,
                attack_cooldown=3.0,
            )

        elif class_type == CharacterClass.ROGUE:
            belongings.weapon = Dagger(
                id=str(uuid.uuid4()),
            )
            belongings.armor = Armor(
                id=str(uuid.uuid4()),
                name="Rogue's Cloak",
                tier=1,
                strength_requirement=9,
            )

        elif class_type == CharacterClass.HUNTRESS:
            belongings.weapon = Bow(
                id=str(uuid.uuid4()),
                name="Spirit Bow",
                damage=2,
                strength_requirement=10,
                attack_cooldown=3.5,
            )

        # SPD identifies a hero's starting gear (HeroClass.java's .identify()), so
        # its STR requirement renders in white (":N") instead of the orange,
        # unidentified "N?" form, and the slot carries no unknown-item tint.
        for slot in belongings.equipped_slots():
            if slot is not None:
                slot.level_known = True
                slot.cursed_known = True

        player = Player(
            id=player_id,
            name=name,
            pos=spawn_pos,
            hp=20,
            max_hp=20,
            attack=3,
            defense=1,
            faction=Faction.PLAYER,
            class_type=class_type,
            belongings=belongings,
            floor_id=1,
            is_admin=is_admin,
        )

        self.players[player_id] = player
        self.depth = 1
        return player

    def _get_stairs_pos(self, tile_type: int, floor_id: Optional[int] = None) -> Position:
        floor = self._get_or_create_floor(floor_id or self.depth)
        for y in range(floor.height):
            for x in range(floor.width):
                if floor.grid[y][x] == tile_type:
                    return Position(x=x, y=y)
        return Position(x=0, y=0)

    def _move_player_to_floor(self, player: Player, target_floor_id: int, spawn_tile: int):
        target_floor_id = max(1, min(MAX_FLOOR_ID, target_floor_id))
        self._get_or_create_floor(target_floor_id)

        player.floor_id = target_floor_id
        player.pos = self._get_stairs_pos(spawn_tile, floor_id=target_floor_id)

        self.depth = target_floor_id

    def next_floor(self, player_id: Optional[str] = None):
        target_players = []
        if player_id and player_id in self.players:
            target_players = [self.players[player_id]]
        elif not player_id and len(self.players) == 1:
            target_players = list(self.players.values())

        for player in target_players:
            if player.floor_id < MAX_FLOOR_ID:
                self._move_player_to_floor(player, player.floor_id + 1, TileType.STAIRS_UP)

    def prev_floor(self, player_id: Optional[str] = None):
        target_players = []
        if player_id and player_id in self.players:
            target_players = [self.players[player_id]]
        elif not player_id and len(self.players) == 1:
            target_players = list(self.players.values())

        for player in target_players:
            if player.floor_id > 1:
                self._move_player_to_floor(player, player.floor_id - 1, TileType.STAIRS_DOWN)

    def _kill_player(self, player: Player, floor: FloorState, floor_id: int):
        # Run the death sequence once: scatter the backpack and mark the spot
        # with a grave (mirrors Hero.reallyDie in Shattered Pixel Dungeon).
        player.death_processed = True

        # Collect passable 8-neighbour cells with no item on them, shuffled.
        free_cells: List[Tuple[int, int]] = []
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                if ox == 0 and oy == 0:
                    continue
                cx, cy = player.pos.x + ox, player.pos.y + oy
                if not (0 <= cx < floor.width and 0 <= cy < floor.height):
                    continue
                if not floor.flags or not floor.flags.passable[cy][cx]:
                    continue
                if any(i.pos and i.pos.x == cx and i.pos.y == cy for i in floor.items.values()):
                    continue
                free_cells.append((cx, cy))
        random.shuffle(free_cells)

        # Drop everything the hero carried — equipped gear plus the backpack's
        # top-level items (sub-bags drop whole). Overflow lands on the death tile.
        dropped_items = [s for s in player.belongings.equipped_slots() if s is not None]
        dropped_items += list(player.belongings.backpack.items)
        for idx, item in enumerate(dropped_items):
            if idx < len(free_cells):
                cx, cy = free_cells[idx]
            else:
                cx, cy = player.pos.x, player.pos.y
            item.pos = Position(x=cx, y=cy)
            floor.items[item.id] = item
        player.belongings = Belongings()
        player.quickslot = QuickSlot()

        # Grave marker on the death tile.
        grave_id = f"grave_{uuid.uuid4().hex[:8]}"
        floor.items[grave_id] = Item(
            id=grave_id,
            name="Grave",
            type="grave",
            pos=Position(x=player.pos.x, y=player.pos.y),
        )

        self.add_event("DEATH", {"target": player.id}, floor_id=floor_id)
