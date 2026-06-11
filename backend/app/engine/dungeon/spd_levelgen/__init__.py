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
"""Byte-for-byte port of SPD's regular-level generation pipeline (rooms,
builders, painters), used to reproduce the original game's dungeon layouts
for a given seed. See /home/artem/.claude/plans/port-a-full-mab-jazzy-elephant.md
for the porting plan and scope notes (layout parity only -- item/mob spawning
depends on hero meta-state and is out of scope here).
"""
