# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
"""Floor generation and content spawning for GameInstance.

Generates each depth's layout using SPD-parity generation (sewers floors 1-5)
or the legacy generator (prison+), then populates it with mobs, items, traps.
"""

import random
import uuid
import zlib
from typing import List, Tuple, Type

from app.engine.dungeon.generator import DungeonGenerator, SewersProfile, TileType
from app.engine.dungeon.dungeon_seed import seed_for_depth
from app.engine.entities.base import (
    Armor,
    Boomerang,
    Bow,
    EntityType,
    Faction,
    HealthPotion,
    RevivingPotion,
    FuryPotion,
    PotionOfStrength,
    PotionOfHaste,
    PotionOfInvisibility,
    PotionOfLevitation,
    PotionOfMindVision,
    PotionOfFrost,
    PotionOfLiquidFlame,
    PotionOfToxicGas,
    PotionOfParalyticGas,
    PotionOfPurity,
    PotionOfExperience,
    ScrollOfRage,
    ScrollOfUpgrade,
    ScrollOfIdentify,
    ScrollOfMagicMapping,
    ScrollOfTeleportation,
    ScrollOfRemoveCurse,
    ScrollOfRecharging,
    ScrollOfLullaby,
    ScrollOfTerror,
    ScrollOfMirrorImage,
    ScrollOfRetribution,
    ScrollOfTransmutation,
    SmallRation,
    Ration,
    Pasty,
    Key,
    Mob as MobEntity,
    Position,
    Staff,
    Stone,
    ThrowableDagger,
    Weapon,
)
from app.engine.entities.mobs import (
    Rat, Snake, Gnoll, Swarm, Crab, Slime,
    AlbinoRat, GnollExile, HermitCrab, CausticSlime,
    Goo,
    Skeleton, Thief, DM100, Guard, Necromancer,
)
from app.engine.game.constants import MAP_HEIGHT, MAP_WIDTH, MAX_FLOOR_ID, SEWERS_MAX_FLOOR, PRISON_MAX_FLOOR
from app.engine.game.floor_state import FloorState
from app.engine.game.spd_adapter import gen_level_to_floor_state


class GenerationMixin:
    def generate_floor(self, depth: int) -> FloorState:
        depth = max(1, min(MAX_FLOOR_ID, depth))
        self.depth = depth

        if depth <= 25:
            floor = self._generate_floor_spd(depth)
        else:
            floor = self._generate_floor_legacy(depth)

        self.floors[depth] = floor
        return floor

    def _generate_floor_spd(self, depth: int) -> FloorState:
        from app.engine.dungeon.spd_random import SPDRandom
        from app.engine.dungeon.spd_levelgen.boss_level import build_boss_floor
        from app.engine.dungeon.spd_levelgen.regular_level import build_floor
        from app.engine.dungeon.spd_levelgen.run_state import is_boss_level

        floor_seed = seed_for_depth(self.master_seed, depth, 0)
        rng = SPDRandom()
        rng.push_generator(floor_seed)
        if is_boss_level(depth):
            gen_level, _rooms = build_boss_floor(rng, depth, self.run_state)
        else:
            gen_level, _rooms = build_floor(rng, depth, self.run_state)
        rng.pop_generator()

        return gen_level_to_floor_state(gen_level, depth)

    def _generate_floor_legacy(self, depth: int) -> FloorState:
        floor_seed = zlib.crc32(f"{self.game_id}:{depth}".encode("utf-8"))
        generator = DungeonGenerator(MAP_WIDTH, MAP_HEIGHT, seed=floor_seed)
        floor: FloorState
        if depth <= SEWERS_MAX_FLOOR:
            sewers_result = generator.generate_sewers(SewersProfile(depth=depth))
            floor = FloorState(
                floor_id=depth,
                grid=sewers_result.grid,
                rooms=sewers_result.rooms,
                mobs={},
                items={},
                region=sewers_result.metadata.region,
                hidden_doors=dict(sewers_result.metadata.hidden_doors),
                locked_doors=dict(sewers_result.metadata.locked_doors),
                traps=dict(sewers_result.metadata.traps),
                key_spawns=dict(sewers_result.metadata.key_spawns),
                generation_meta={
                    "layout_kind": sewers_result.metadata.layout_kind,
                    "room_ids_by_kind": sewers_result.metadata.room_ids_by_kind,
                    "room_connections": sewers_result.metadata.room_connections,
                    "start_room_id": sewers_result.metadata.start_room_id,
                    "end_room_id": sewers_result.metadata.end_room_id,
                    "seed": sewers_result.metadata.seed,
                },
            )
        elif depth == 5:
            grid, rooms = generator.generate_boss_floor()
            floor = FloorState(
                floor_id=depth,
                grid=grid,
                rooms=rooms,
                mobs={},
                items={},
                region="sewers",
                locked_doors=dict(getattr(generator, "boss_locked_doors", {})),
            )
        elif depth <= PRISON_MAX_FLOOR:
            grid, rooms = generator.generate(10 + depth, 4, 8 + (depth // 10))
            floor = FloorState(
                floor_id=depth,
                grid=grid,
                rooms=rooms,
                mobs={},
                items={},
                region="prison",
            )
        else:
            grid, rooms = generator.generate(10 + depth, 4, 8 + (depth // 10))
            floor = FloorState(
                floor_id=depth,
                grid=grid,
                rooms=rooms,
                mobs={},
                items={},
                region="legacy",
            )

        floor.rebuild_flags()
        self._spawn_content(floor)
        return floor

    def _is_in_safe_room(self, floor: FloorState, x: int, y: int) -> bool:
        if not floor.rooms:
            return False

        start_room = floor.rooms[0]
        end_room = floor.rooms[-1]

        if (
            start_room.x <= x < start_room.x + start_room.width
            and start_room.y <= y < start_room.y + start_room.height
        ):
            return True

        if (
            end_room.x <= x < end_room.x + end_room.width
            and end_room.y <= y < end_room.y + end_room.height
        ):
            return True

        return False

    def _is_in_entrance_room(self, floor: FloorState, x: int, y: int) -> bool:
        if not floor.rooms:
            return False

        room = floor.rooms[0]  # entrance / up-stairs room
        return (
            room.x <= x < room.x + room.width
            and room.y <= y < room.y + room.height
        )

    def _get_sewers_rotation(self, floor_id: int) -> List[Type[MobEntity]]:
        rotations = {
            1: [Rat, Rat, Rat, Snake],
            2: [Rat, Rat, Snake, Gnoll, Gnoll],
            3: [Rat, Snake, Gnoll, Gnoll, Gnoll, Swarm, Crab],
            4: [Gnoll, Swarm, Crab, Crab, Slime, Slime],
        }
        return rotations.get(floor_id, [Rat])

    def _get_prison_rotation(self, floor_id: int) -> List[Type[MobEntity]]:
        rotations = {
            6: [Skeleton, Skeleton, Thief, DM100],
            7: [Skeleton, Thief, DM100, DM100, Guard],
            8: [Thief, DM100, Guard, Guard, Necromancer],
            9: [DM100, Guard, Necromancer, Necromancer],
        }
        return rotations.get(floor_id, [Skeleton])

    def _get_mob_limit(self, floor_id: int) -> int:
        if floor_id == 1:
            return 8
        if floor_id <= 4:
            return 3 + floor_id % 5 + random.randint(0, 2)
        return 5 + floor_id

    def _spawn_mob_at(self, cls: Type[MobEntity], x: int, y: int) -> MobEntity:
        mob_id = str(uuid.uuid4())
        # attack_cooldown comes from the mob class, decoupled from movement
        # `speed` (a fast mover chases quicker but does not attack quicker).
        mob = cls(id=mob_id, pos=Position(x=x, y=y), faction=Faction.DUNGEON)
        return mob

    def _spawn_content(self, floor: FloorState):
        floor_tiles = [
            (x, y)
            for y in range(floor.height)
            for x in range(floor.width)
            if floor.grid[y][x] in [
                TileType.FLOOR,
                TileType.FLOOR_WOOD,
                TileType.FLOOR_WATER,
                TileType.FLOOR_COBBLE,
                TileType.FLOOR_GRASS,
            ]
        ]

        unsafe_floor_tiles = [
            pos for pos in floor_tiles if not self._is_in_safe_room(floor, pos[0], pos[1])
        ]

        self._spawn_floor_keys(floor)
        blocked_item_tiles = {
            (item.pos.x, item.pos.y) for item in floor.items.values() if item.pos is not None
        }
        if blocked_item_tiles:
            floor_tiles = [pos for pos in floor_tiles if pos not in blocked_item_tiles]
            unsafe_floor_tiles = [pos for pos in unsafe_floor_tiles if pos not in blocked_item_tiles]

        if floor.floor_id % 5 == 0:
            self._spawn_boss(floor, unsafe_floor_tiles)

        if floor.floor_id != 5 and floor.floor_id != 10:
            if floor.floor_id <= SEWERS_MAX_FLOOR:
                rotation = self._get_sewers_rotation(floor.floor_id)
                rare_chance = 0.02
                rare_alts = {
                    Rat: AlbinoRat,
                    Gnoll: GnollExile,
                    Crab: HermitCrab,
                    Slime: CausticSlime,
                }
            elif floor.floor_id <= PRISON_MAX_FLOOR:
                rotation = self._get_prison_rotation(floor.floor_id)
                rare_chance = 0.0
                rare_alts = {}
            else:
                rotation = self._get_sewers_rotation(floor.floor_id)
                rare_chance = 0.02
                rare_alts = {
                    Rat: AlbinoRat,
                    Gnoll: GnollExile,
                    Crab: HermitCrab,
                    Slime: CausticSlime,
                }
            mob_limit = self._get_mob_limit(floor.floor_id)
            floor.mob_limit = mob_limit

            spawn_count = mob_limit if floor.floor_id != 1 else min(mob_limit, len(rotation) * 2)
            for i in range(spawn_count):
                if not unsafe_floor_tiles:
                    break
                x, y = unsafe_floor_tiles.pop(random.randint(0, len(unsafe_floor_tiles) - 1))
                cls = rotation[i % len(rotation)]
                rare_cls = rare_alts.get(cls)
                if rare_cls and random.random() < rare_chance:
                    cls = rare_cls
                mob = self._spawn_mob_at(cls, x, y)
                floor.mobs[mob.id] = mob

        _ALL_POTIONS = [
            HealthPotion, RevivingPotion, FuryPotion,
            PotionOfStrength, PotionOfHaste, PotionOfInvisibility, PotionOfLevitation,
            PotionOfMindVision, PotionOfFrost, PotionOfLiquidFlame, PotionOfToxicGas,
            PotionOfParalyticGas, PotionOfPurity, PotionOfExperience,
        ]
        _ALL_SCROLLS = [
            ScrollOfRage, ScrollOfUpgrade, ScrollOfIdentify, ScrollOfMagicMapping,
            ScrollOfTeleportation, ScrollOfRemoveCurse, ScrollOfRecharging, ScrollOfLullaby,
            ScrollOfTerror, ScrollOfMirrorImage, ScrollOfRetribution, ScrollOfTransmutation,
        ]
        _ALL_FOOD = [SmallRation, Ration, Ration, Pasty]

        num_items = 4 + random.randint(0, 3)
        for _ in range(num_items):
            if not floor_tiles:
                break
            x, y = floor_tiles.pop(random.randint(0, len(floor_tiles) - 1))
            item_id = str(uuid.uuid4())

            rand = random.random()
            if rand < 0.2:
                floor.items[item_id] = Weapon(
                    id=item_id,
                    name=random.choice(["Rusty Sword", "Wooden Club", "Dagger"]),
                    pos=Position(x=x, y=y),
                    damage=2 + random.randint(0, 2),
                    range=1,
                    strength_requirement=10 + random.randint(-2, 2),
                    attack_cooldown=3.0 if "Dagger" not in "Rusty Sword, Wooden Club" else 1.5,
                )
            elif rand < 0.3:
                floor.items[item_id] = Bow(
                    id=item_id,
                    name="Old Bow",
                    pos=Position(x=x, y=y),
                    damage=2 + random.randint(0, 2),
                    strength_requirement=10,
                    attack_cooldown=3.5,
                )
            elif rand < 0.4:
                floor.items[item_id] = Staff(
                    id=item_id,
                    name="Magic Staff",
                    pos=Position(x=x, y=y),
                    damage=1 + random.randint(0, 2),
                    magic_damage=2 + random.randint(0, 2),
                    strength_requirement=10,
                )
            elif rand < 0.6:
                armor_tiers = [
                    ("Cloth Armor", 1, 10),
                    ("Leather Armor", 2, 12),
                    ("Mail Armor", 3, 14),
                    ("Scale Armor", 4, 16),
                ]
                tier_idx = min(len(armor_tiers) - 1, (floor.floor_id - 1) // 4)
                name, tier, str_req = random.choice(armor_tiers[:tier_idx + 1])
                floor.items[item_id] = Armor(
                    id=item_id,
                    name=name,
                    tier=tier,
                    pos=Position(x=x, y=y),
                    strength_requirement=str_req,
                )
            elif rand < 0.65:
                t_rand = random.random()
                if t_rand < 0.5:
                    floor.items[item_id] = Stone(id=item_id, pos=Position(x=x, y=y), damage=1, range=5)
                elif t_rand < 0.8:
                    floor.items[item_id] = ThrowableDagger(id=item_id, pos=Position(x=x, y=y), damage=4, range=4)
                else:
                    floor.items[item_id] = Boomerang(id=item_id, pos=Position(x=x, y=y), damage=3, range=6)
            elif rand < 0.80:
                cls = random.choice(_ALL_POTIONS)
                floor.items[item_id] = cls(id=item_id, pos=Position(x=x, y=y))
            elif rand < 0.93:
                cls = random.choice(_ALL_SCROLLS)
                floor.items[item_id] = cls(id=item_id, pos=Position(x=x, y=y))
            else:
                cls = random.choice(_ALL_FOOD)
                floor.items[item_id] = cls(id=item_id, pos=Position(x=x, y=y))

    def _spawn_floor_keys(self, floor: FloorState):
        for key_id, (x, y) in floor.key_spawns.items():
            item_id = str(uuid.uuid4())
            floor.items[item_id] = Key(
                id=item_id,
                name="Rusty Key",
                pos=Position(x=x, y=y),
                key_id=key_id,
            )

    def _spawn_boss(self, floor: FloorState, floor_tiles: List[Tuple[int, int]]):
        if floor.floor_id in (5, 10, 15, 20, 25):
            # Bosses for these floors are placed by the boss floor builder (spd_adapter)
            return
        else:
            if not floor_tiles:
                return
            x, y = floor_tiles.pop(random.randint(0, len(floor_tiles) - 1))
            boss_id = str(uuid.uuid4())
            floor.mobs[boss_id] = MobEntity(
                id=boss_id,
                type=EntityType.BOSS,
                name=f"Floor {floor.floor_id} Boss",
                pos=Position(x=x, y=y),
                hp=100 + (floor.floor_id * 20),
                max_hp=100 + (floor.floor_id * 20),
                attack=10 + floor.floor_id,
                defense=5 + floor.floor_id,
                attack_cooldown=3.0,
                faction=Faction.DUNGEON,
                exp=10 + floor.floor_id,
            )
