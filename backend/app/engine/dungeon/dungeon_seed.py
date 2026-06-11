"""Port of DungeonSeed (seed-string <-> long conversion) and
Dungeon.seedForDepth (per-floor seed derivation), preserving SPD's exact
algorithms so a given seed string produces identical per-floor RNG state.

Reference:
- .../utils/DungeonSeed.java
- .../Dungeon.java (initSeed, seedForDepth/seedCurDepth)
"""

from __future__ import annotations

import re

from app.engine.dungeon.spd_random import SPDRandom

TOTAL_SEEDS = 5_429_503_678_976  # 26**9

_CODE_RE = re.compile(r"[-\s]")


def convert_from_code(code: str) -> int:
    """9-char base-26 (A-Z) seed code -> long. Raises ValueError if malformed."""
    if len(code) == 11 and code[3] == "-" and code[7] == "-":
        code = code.upper()

    code = _CODE_RE.sub("", code)

    if len(code) != 9:
        raise ValueError("codes must be 9 A-Z characters.")

    result = 0
    for i in range(8, -1, -1):
        c = code[i]
        if c > "Z" or c < "A":
            raise ValueError("codes must be 9 A-Z characters.")
        result += (ord(c) - 65) * (26 ** (8 - i))
    return result


_DIGIT_TO_LETTER = str.maketrans("0123456789abcdefghijklmnop",
                                 "ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def convert_to_code(seed: int) -> str:
    """long -> 9-char base-26 seed code (with dashes for readability)."""
    if seed < 0 or seed >= TOTAL_SEEDS:
        raise ValueError("seeds must be within the range [0, TOTAL_SEEDS)")

    interim = _to_base26(seed)
    chars = []
    for i in range(9):
        if i < len(interim):
            chars.append(interim[i].translate(_DIGIT_TO_LETTER))
        else:
            chars.insert(0, "A")

    code = "".join(chars)
    return f"{code[0:3]}-{code[3:6]}-{code[6:9]}"


def _to_base26(value: int) -> str:
    if value == 0:
        return "0"
    digits = "0123456789abcdefghijklmnop"
    out = []
    while value > 0:
        value, rem = divmod(value, 26)
        out.append(digits[rem])
    return "".join(reversed(out))


def convert_from_text(text: str) -> int:
    """Mirrors DungeonSeed.convertFromText: try code, then numeric, then hash."""
    if not text:
        return -1

    try:
        return convert_from_code(text)
    except ValueError:
        pass

    stripped = re.sub(r"\s", "", text)
    try:
        return int(stripped) % TOTAL_SEEDS
    except ValueError:
        pass

    total = 0
    for c in text:
        total = _to_signed64(31 * total + ord(c))
    if total < 0:
        total += 0x7FFFFFFFFFFFFFFF  # Long.MAX_VALUE
    return total % TOTAL_SEEDS


def _to_signed64(x: int) -> int:
    x &= (1 << 64) - 1
    return x - (1 << 64) if x >= (1 << 63) else x


def format_text(text: str) -> str:
    try:
        return convert_to_code(convert_from_code(text))
    except ValueError:
        return text


def seed_for_depth(master_seed: int, depth: int, branch: int = 0) -> int:
    """Port of Dungeon.seedForDepth: derive a per-floor seed from the master
    seed by pushing it onto the generator stack, burning `depth + 30*branch`
    Long() draws, and taking the next Long() as the floor's seed."""
    look_ahead = depth + 30 * branch

    rng = SPDRandom()
    rng.push_generator(master_seed)
    for _ in range(look_ahead):
        rng.Long()
    result = rng.Long()
    rng.pop_generator()
    return result
