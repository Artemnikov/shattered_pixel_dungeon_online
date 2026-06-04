import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.entities.base import Position
from app.engine.entities.mobs import Swarm, Rat
from app.engine.systems.combat import resolve_melee_attack


def test_swarm_defense_proc_returns_damage():
    """defense_proc is contracted to return the (possibly modified) damage so
    the combat resolver can keep applying it. Swarm must not return None."""
    swarm = Swarm(id="s1", pos=Position(x=5, y=5))
    floor_mobs = {swarm.id: swarm}
    out = swarm.defense_proc(5, attacker=None, floor_mobs=floor_mobs, tile_x=5, tile_y=5)
    assert out == 5


def test_attacking_swarm_does_not_crash():
    """Regression: hitting a Swarm used to raise
    TypeError: '<=' not supported between 'NoneType' and 'int' because
    defense_proc returned None into combat.py's `if raw_damage <= 0`."""
    swarm = Swarm(id="s1", pos=Position(x=5, y=5), defense_skill=0)
    attacker = Rat(id="r1", pos=Position(x=4, y=5), attack_skill=100)
    floor_mobs = {swarm.id: swarm, attacker.id: attacker}

    result = resolve_melee_attack(attacker, swarm, floor_mobs, 5, 5, is_in_los=None)
    assert isinstance(result["damage"], int)
    assert result["hit"] is True
