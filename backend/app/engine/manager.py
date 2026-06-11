"""Central game state for a single multiplayer session.

`GameInstance` owns all game state and coordinates the engine subsystems. The
implementation is split into per-concern mixins under ``app.engine.game`` so each
area stays small and editable in isolation; this module composes them and holds
the shared constructor.

Re-exports below (``FloorState``, ``TileType``, ``Position``, ``CharacterClass``,
the module constants) keep the historical ``from app.engine.manager import ...``
import paths working for callers and tests.
"""

from typing import Dict, List, Optional, Tuple

# Re-exported for backward-compatible imports (main.py, tests).
from app.engine.dungeon.generator import TileType
from app.engine.entities.base import (
    CharacterClass,
    Difficulty,
    Player,
    Position,
)

from app.engine.game.constants import (
    AUTO_MOVE_INTERVAL,
    HEAL_TICK_INTERVAL,
    MAP_HEIGHT,
    MAP_WIDTH,
    MAX_FLOOR_ID,
    NO_RESPAWN_FLOORS,
    PASSIVE_REGEN_INTERVAL,
    RESPAWN_TURNS,
    ROOM_HEAL_AMOUNT,
    SEWERS_MAX_FLOOR,
)
from app.engine.game.floor_state import FloorState
from app.engine.game.armor_abilities import ArmorAbilitiesMixin
from app.engine.game.events import EventsMixin
from app.engine.game.floors import FloorAccessMixin
from app.engine.game.generation import GenerationMixin
from app.engine.game.items import ItemsMixin
from app.engine.game.movement import MovementCombatMixin
from app.engine.game.players import PlayersMixin
from app.engine.game.rogue import RogueMixin
from app.engine.game.serialization import SerializationMixin
from app.engine.game.talents import TalentsMixin
from app.engine.game.tengu_arena import PrisonBossMixin
from app.engine.game.ai_goo import GooAIMixin
from app.engine.game.ai_dwarf_king import DwarfKingAIMixin
from app.engine.game.ai_yog_dzewa import YogDzewaAIMixin
from app.engine.game.ai_demon_spawner import DemonSpawnerAIMixin
from app.engine.game.ai_pylon import PylonAIMixin
from app.engine.game.ai_dm300 import DM300AIMixin
from app.engine.game.ai_necromancer import NecromancerAIMixin
from app.engine.game.ai_tengu import TenguAIMixin
from app.engine.game.tick import TickMixin
from app.engine.game.vision import VisionMixin
from app.engine.game.world import WorldInteractionMixin


class GameInstance(
    FloorAccessMixin,
    EventsMixin,
    GenerationMixin,
    PlayersMixin,
    WorldInteractionMixin,
    MovementCombatMixin,
    ItemsMixin,
    PrisonBossMixin,
    GooAIMixin,
    DwarfKingAIMixin,
    YogDzewaAIMixin,
    DemonSpawnerAIMixin,
    PylonAIMixin,
    DM300AIMixin,
    NecromancerAIMixin,
    TenguAIMixin,
    TickMixin,
    ArmorAbilitiesMixin,
    TalentsMixin,
    RogueMixin,
    VisionMixin,
    SerializationMixin,
):
    def __init__(self, game_id: str, seed: Optional[str] = None):
        self.game_id = game_id
        self.depth = 1  # Compatibility view for single-floor tests/legacy callers.

        self.players: Dict[str, Player] = {}
        self.floors: Dict[int, FloorState] = {}
        self.events: List[dict] = []

        # Per-tick shadowcasting caches. Open doors depend on occupancy, which
        # changes as entities move, so both are invalidated every tick (and on
        # any movement) via _invalidate_fov_cache().
        self._fov_cache: Dict[Tuple[int, int, int, int], List[bool]] = {}
        self._blocking_cache: Dict[int, List[bool]] = {}

        self.difficulty = Difficulty.NORMAL
        self.player_count = 0

        # Lobby challenge flags (SPD Challenges), comma-separated set parsed
        # via set_challenges(). Currently only "stronger_bosses" is supported.
        self.challenges: set = set()

        # Shared per-run identification knowledge (co-op semantics, mirrors SPD's
        # per-Dungeon catalog): once any player IDs a potion/scroll kind, the whole
        # party knows it. `kind_labels` holds the scrambled per-run display names
        # for still-unidentified kinds.
        self.identified_kinds: set = set()
        self.kind_labels: Dict[str, str] = {}
        self.kind_appearance: Dict[str, int] = {}
        self._appearance_used: Dict[str, set] = {"potion": set(), "scroll": set()}

        # Global drop limiters
        self.drop_counters: Dict[str, int] = {}

        # Per-run boss score tracking (SPD Statistics.bossScores)
        # Indices: 0=Goo, 1=Tengu, 2=DM300, 3=Dwarf King, 4=Yog
        self.boss_scores: Dict[int, int] = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
        # Badge eligibility — set when entering a boss floor, cleared on
        # avoidable damage (SPD Statistics.qualifiedForBossChallengeBadge)
        self.qualified_for_boss_challenge: bool = False

        # Seed + RunState for SPD-parity level generation.
        if seed:
            from app.engine.dungeon.dungeon_seed import convert_from_text
            self.master_seed = convert_from_text(seed)
        else:
            import zlib
            self.master_seed = zlib.crc32(game_id.encode("utf-8")) % 5_429_503_678_976

        from app.engine.dungeon.spd_levelgen.run_state import RunState
        from app.engine.dungeon.spd_random import SPDRandom

        self.run_state = RunState()
        init_rng = SPDRandom()
        init_rng.push_generator(self.master_seed + 1)
        self.run_state.init_for_run(init_rng)
        init_rng.pop_generator()

        self.generate_floor(1)
