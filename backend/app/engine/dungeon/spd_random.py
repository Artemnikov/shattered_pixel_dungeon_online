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
"""Port of SPD's RNG stack (com.watabou.utils.Random), which wraps
java.util.Random (a 48-bit LCG) behind a generator stack seeded via an
MX3 scramble. Byte-for-byte parity with the original is required so that
a given seed produces identical dungeon layouts.

Reference: shattered-pixel-dungeon SPD-classes/.../com/watabou/utils/Random.java
"""

from __future__ import annotations

import struct
from typing import List, Optional, Sequence, TypeVar

T = TypeVar("T")

MASK48 = (1 << 48) - 1
MASK64 = (1 << 64) - 1
LCG_MULTIPLIER = 0x5DEECE66D
LCG_ADDEND = 0xB
MX3_CONST = 0xBEA225F9EB34556D


def _to_int32(x: int) -> int:
    x &= 0xFFFFFFFF
    return x - 0x100000000 if x >= 0x80000000 else x


def to_f32(x: float) -> float:
    """Round a Python double to the nearest float32, matching Java `float` arithmetic."""
    return struct.unpack(">f", struct.pack(">f", x))[0]


def scramble_seed(seed: int) -> int:
    """MX3 hash by Jon Maiga (CC0), as used by Random.pushGenerator(long)."""
    seed &= MASK64
    seed ^= seed >> 32
    seed = (seed * MX3_CONST) & MASK64
    seed ^= seed >> 29
    seed = (seed * MX3_CONST) & MASK64
    seed ^= seed >> 32
    seed = (seed * MX3_CONST) & MASK64
    seed ^= seed >> 29
    return seed


class JavaRandom:
    """Reimplementation of java.util.Random's 48-bit LCG."""

    def __init__(self, seed: int):
        self.set_seed(seed)

    def set_seed(self, seed: int) -> None:
        self._seed = (seed ^ LCG_MULTIPLIER) & MASK48

    def next(self, bits: int) -> int:
        self._seed = (self._seed * LCG_MULTIPLIER + LCG_ADDEND) & MASK48
        r = self._seed >> (48 - bits)
        if bits == 32 and r >= 0x80000000:
            r -= 0x100000000
        return r

    def next_int(self) -> int:
        return self.next(32)

    def next_int_bound(self, bound: int) -> int:
        if bound <= 0:
            raise ValueError("bound must be positive")
        if (bound & -bound) == bound:  # bound is a power of 2
            return _to_int32((bound * self.next(31)) >> 31)
        while True:
            bits = self.next(31)
            val = bits % bound
            if _to_int32(bits - val + (bound - 1)) >= 0:
                return val

    def next_long(self) -> int:
        hi = self.next(32)
        lo = self.next(32)
        return (hi << 32) + lo

    def next_float(self) -> float:
        return self.next(24) / float(1 << 24)

    def next_boolean(self) -> bool:
        return self.next(1) != 0

    def shuffle(self, seq: List[T]) -> None:
        """Fisher-Yates matching java.util.Collections.shuffle."""
        for i in range(len(seq) - 1, 0, -1):
            j = self.next_int_bound(i + 1)
            seq[i], seq[j] = seq[j], seq[i]


class SPDRandom:
    """Port of com.watabou.utils.Random's generator stack + convenience API."""

    def __init__(self):
        self._generators: List[JavaRandom] = [JavaRandom(_unseeded_long())]

    # -- generator stack -------------------------------------------------
    def push_generator(self, seed: Optional[int] = None) -> None:
        if seed is None:
            self._generators.append(JavaRandom(_unseeded_long()))
        else:
            self._generators.append(JavaRandom(scramble_seed(seed)))

    def pop_generator(self) -> None:
        if len(self._generators) == 1:
            raise RuntimeError("tried to pop the last random number generator!")
        self._generators.pop()

    def _gen(self) -> JavaRandom:
        return self._generators[-1]

    # -- core draws -------------------------------------------------------
    def Float(self) -> float:
        return self._gen().next_float()

    def FloatMax(self, max_: float) -> float:
        return to_f32(to_f32(self.Float()) * to_f32(max_))

    def FloatRange(self, min_: float, max_: float) -> float:
        return to_f32(min_ + self.FloatMax(to_f32(max_ - min_)))

    def Int(self) -> int:
        return self._gen().next_int()

    def IntMax(self, max_: int) -> int:
        if max_ <= 0:
            return 0
        return self._gen().next_int_bound(max_)

    def IntMinMax(self, min_: int, max_: int) -> int:
        return min_ + self.IntMax(max_ - min_)

    def IntRange(self, min_: int, max_: int) -> int:
        return min_ + self.IntMax(max_ - min_ + 1)

    def NormalIntRange(self, min_: int, max_: int) -> int:
        return min_ + int((self.Float() + self.Float()) * (max_ - min_ + 1) / 2.0)

    def InvNormalIntRange(self, min_: int, max_: int) -> int:
        roll1, roll2 = self.Float(), self.Float()
        if abs(roll1 - 0.5) >= abs(roll2 - 0.5):
            return min_ + int(roll1 * (max_ - min_ + 1))
        return min_ + int(roll2 * (max_ - min_ + 1))

    def Long(self) -> int:
        return self._gen().next_long()

    def LongMax(self, max_: int) -> int:
        result = self.Long()
        if result < 0:
            result += 0x7FFFFFFFFFFFFFFF  # Long.MAX_VALUE
        return result % max_

    def chances(self, weights: Sequence[float]) -> int:
        total = sum(max(0.0, w) for w in weights)
        if total <= 0:
            return -1
        value = self.FloatMax(to_f32(total))
        running = 0.0
        for i, w in enumerate(weights):
            running = to_f32(running + to_f32(max(0.0, w)))
            if value < running:
                return i
        return -1

    def element(self, seq: Sequence[T], max_: Optional[int] = None) -> T:
        return seq[self.IntMax(len(seq) if max_ is None else max_)]

    def shuffle(self, seq: List[T]) -> None:
        """Matches Random.shuffle(List<T>) -> Collections.shuffle (reverse Fisher-Yates)."""
        self._gen().shuffle(seq)

    def shuffle_array(self, seq: List[T]) -> None:
        """Matches Random.shuffle(T[]) -- a *different* (forward) shuffle algorithm
        than the List overload; SPD code uses both, and they diverge for the same
        RNG state, so callers must pick the one matching the Java call site."""
        for i in range(len(seq) - 1):
            j = self.IntMinMax(i, len(seq))
            if j != i:
                seq[i], seq[j] = seq[j], seq[i]


def _unseeded_long() -> int:
    """Stand-in for `new java.util.Random()` (system-seeded). Only used for
    non-deterministic generator pushes; never on the deterministic path."""
    import random as _random

    return _random.getrandbits(63)
