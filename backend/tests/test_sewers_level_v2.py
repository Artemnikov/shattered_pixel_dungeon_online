"""End-to-end tests for the Phase D pipeline (sewers_level.generate_sewers_level).

Confirms the new pipeline:
- produces a deterministic grid for a fixed seed
- emits only known tile IDs (no leftover wall subtypes)
- yields a single connected component over the room graph
- has the expected entrance/exit tiles in the grid
- can be selected via DungeonGenerator(...).generate_sewers(use_v2_pipeline=True)
"""

from collections import defaultdict

from app.engine.dungeon.constants import TileType
from app.engine.dungeon.generator import DungeonGenerator
from app.engine.dungeon.models import SewersProfile
from app.engine.dungeon.sewers_level import generate_sewers_level


_VALID_TILES = {
    TileType.VOID, TileType.WALL, TileType.FLOOR, TileType.DOOR,
    TileType.STAIRS_UP, TileType.STAIRS_DOWN, TileType.FLOOR_WATER,
    TileType.FLOOR_GRASS, TileType.HIGH_GRASS, TileType.WALL_DECO,
    TileType.EMPTY_DECO, TileType.LOCKED_DOOR, TileType.SECRET_DOOR,
    TileType.TRAP,
}


def _components(rooms, edges):
    adj = defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    seen = set()
    comps = 0
    for r in rooms:
        if r.room_id in seen:
            continue
        comps += 1
        stack = [r.room_id]
        while stack:
            v = stack.pop()
            if v in seen:
                continue
            seen.add(v)
            stack.extend(adj[v])
    return comps


def test_v2_pipeline_deterministic():
    a = generate_sewers_level(60, 40, SewersProfile(depth=1), seed=12345)
    b = generate_sewers_level(60, 40, SewersProfile(depth=1), seed=12345)
    assert a.grid == b.grid
    assert [r.room_id for r in a.rooms] == [r.room_id for r in b.rooms]


def test_v2_pipeline_only_emits_known_tiles():
    r = generate_sewers_level(60, 40, SewersProfile(depth=1), seed=42)
    seen = {t for row in r.grid for t in row}
    unknown = seen - _VALID_TILES
    assert not unknown, f"unknown tile IDs in grid: {unknown}"


def test_v2_pipeline_room_graph_is_connected():
    r = generate_sewers_level(60, 40, SewersProfile(depth=1), seed=42)
    assert r.rooms, "must produce at least one room"
    assert _components(r.rooms, r.metadata.room_connections) == 1


def test_v2_pipeline_has_entrance_and_exit():
    r = generate_sewers_level(60, 40, SewersProfile(depth=1), seed=42)
    flat = [t for row in r.grid for t in row]
    assert flat.count(TileType.STAIRS_UP) >= 1
    assert flat.count(TileType.STAIRS_DOWN) >= 1


def test_use_v2_pipeline_flag_on_generator():
    g = DungeonGenerator(60, 40, seed=99)
    r = g.generate_sewers(SewersProfile(depth=1), use_v2_pipeline=True)
    assert r.metadata.layout_kind in {"loop", "figure_eight"}
    assert _components(r.rooms, r.metadata.room_connections) == 1
