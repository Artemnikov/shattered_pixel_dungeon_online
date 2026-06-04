from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Buff(BaseModel):
    id: str
    type: str
    remaining: float = 0.0
    level: int = 0
    source_id: Optional[str] = None
    interval: float = 1.0
    stack_mode: str = "replace"  # "replace" | "extend" | "stack"


def add_buff(buffs: list[Buff], buff_type: str, duration: float, level: int = 0, source_id: Optional[str] = None, stack_mode: str = "replace") -> Buff:
    existing = next((b for b in buffs if b.type == buff_type), None)
    if existing:
        if stack_mode == "replace":
            existing.remaining = duration
            existing.level = level
            existing.source_id = source_id
            return existing
        elif stack_mode == "extend":
            existing.remaining = max(existing.remaining, duration)
            existing.level = max(existing.level, level)
            return existing
        elif stack_mode == "stack":
            existing.remaining += duration
            existing.level += level
            return existing
    import uuid
    buff = Buff(
        id=str(uuid.uuid4()),
        type=buff_type,
        remaining=duration,
        level=level,
        source_id=source_id,
        stack_mode=stack_mode,
    )
    buffs.append(buff)
    return buff


def remove_buff(buffs: list[Buff], buff_type: str) -> Optional[Buff]:
    for i, b in enumerate(buffs):
        if b.type == buff_type:
            return buffs.pop(i)
    return None


def has_buff(buffs: list[Buff], buff_type: str) -> bool:
    return any(b.type == buff_type for b in buffs)


def get_buff(buffs: list[Buff], buff_type: str) -> Optional[Buff]:
    return next((b for b in buffs if b.type == buff_type), None)


def process_buffs(buffs: list[Buff], dt: float) -> list[str]:
    removed: list[str] = []
    for b in list(buffs):
        b.remaining -= dt
        if b.remaining <= 0:
            buffs.remove(b)
            removed.append(b.type)
    return removed
