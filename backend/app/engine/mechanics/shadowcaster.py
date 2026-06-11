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
"""Recursive shadowcasting field-of-view.

A faithful Python port of Shattered Pixel Dungeon's
`core/.../mechanics/ShadowCaster.java`, which is itself based on
http://www.roguebasin.com/index.php?title=FOV_using_recursive_shadowcasting

The algorithm, the circular `ROUNDING` table, the 0.5 cell-centre offsets, the
distance-2 corner fill, and the octant scan order are all reproduced 1:1 so the
remake's vision matches the original game exactly. Operates on flat 1-D lists
indexed `y * w + x` (matching the Java math); callers convert to/from the 2-D
floor maps at the boundary.
"""

import logging
import math
from typing import List

logger = logging.getLogger(__name__)

MAX_DISTANCE = 20

# max length of rows as FOV moves out, for each FOV distance. This is used to
# make the overall FOV circular instead of square. Mirrors the Java `static`
# block: ROUNDING[i][j] = min(j, round(i * cos(asin(j / (i + 0.5))))).
ROUNDING: List[List[int]] = [[] for _ in range(MAX_DISTANCE + 1)]
for _i in range(1, MAX_DISTANCE + 1):
    ROUNDING[_i] = [0] * (_i + 1)
    for _j in range(1, _i + 1):
        # testing the middle of a cell, so we use i + 0.5
        ROUNDING[_i][_j] = int(min(
            _j,
            round(_i * math.cos(math.asin(_j / (_i + 0.5)))),
        ))


def cast_shadow(x: int, y: int, w: int, field_of_view: List[bool],
                blocking: List[bool], distance: int) -> None:
    """Fill `field_of_view` (flat, length w*h) with visibility from (x, y).

    `blocking` is the flat LOS-blocking map. `distance` is the view radius,
    capped at MAX_DISTANCE.
    """
    if distance >= MAX_DISTANCE:
        distance = MAX_DISTANCE

    for i in range(len(field_of_view)):
        field_of_view[i] = False

    # set source cell to true
    field_of_view[y * w + x] = True

    # scans octants, clockwise
    try:
        _scan_octant(distance, field_of_view, blocking, 1, x, y, w, 0.0, 1.0, +1, -1, False)
        _scan_octant(distance, field_of_view, blocking, 1, x, y, w, 0.0, 1.0, -1, +1, True)
        _scan_octant(distance, field_of_view, blocking, 1, x, y, w, 0.0, 1.0, +1, +1, True)
        _scan_octant(distance, field_of_view, blocking, 1, x, y, w, 0.0, 1.0, +1, +1, False)
        _scan_octant(distance, field_of_view, blocking, 1, x, y, w, 0.0, 1.0, -1, +1, False)
        _scan_octant(distance, field_of_view, blocking, 1, x, y, w, 0.0, 1.0, +1, -1, True)
        _scan_octant(distance, field_of_view, blocking, 1, x, y, w, 0.0, 1.0, -1, -1, True)
        _scan_octant(distance, field_of_view, blocking, 1, x, y, w, 0.0, 1.0, -1, -1, False)
    except Exception:
        logger.exception("shadowcast failed; blanking FOV")
        for i in range(len(field_of_view)):
            field_of_view[i] = False


def _scan_octant(distance: int, fov: List[bool], blocking: List[bool], row: int,
                 x: int, y: int, w: int, l_slope: float, r_slope: float,
                 m_x: int, m_y: int, m_xy: bool) -> None:
    """Scan a single 45-degree octant of the FOV.

    This adds up to a whole FOV by mirroring in X (m_x), Y (m_y), and X=Y (m_xy).
    """
    in_blocking = False

    if distance == 2:
        # at a visibility distance of 2 we fill in the corners of vision as
        # otherwise this vision range disproportionately punishes diagonal
        # movement, even though removing corners is technically correct
        rounding_at_dist = list(ROUNDING[distance])
        rounding_at_dist[2] = 2
    else:
        rounding_at_dist = ROUNDING[distance]

    # calculations are offset by 0.5 because FOV is coming from the centre of
    # the source cell

    # for each row, starting with the current one
    while row <= distance:

        # if we have negative space to traverse, just quit.
        if r_slope < l_slope:
            return

        # we offset by slightly less than 0.5 to account for slopes just
        # touching a cell
        if l_slope == 0:
            start = 0
        else:
            start = int(math.floor((row - 0.5) * l_slope + 0.499))

        if r_slope == 1:
            end = rounding_at_dist[row]
        else:
            end = min(rounding_at_dist[row],
                      int(math.ceil((row + 0.5) * r_slope - 0.499)))

        # coordinates of source
        cell = x + y * w

        # plus coordinates of current cell (including mirroring in x, y, and x=y)
        if m_xy:
            cell += m_x * start * w + m_y * row
        else:
            cell += m_x * start + m_y * row * w

        # for each column in this row
        col = start
        while col <= end:

            # handles the error case of the slope value at the end of a cell
            # being 1 farther along than at the beginning of the cell, and that
            # earlier cell is vision blocking
            if (col == end and in_blocking
                    and int(math.ceil((row - 0.5) * r_slope - 0.499)) != end):
                break

            fov[cell] = True

            if blocking[cell]:
                if not in_blocking:
                    in_blocking = True

                    # start a new scan, 1 row deeper, ending at the left side
                    # of current cell
                    if col != start:
                        _scan_octant(distance, fov, blocking, row + 1, x, y, w, l_slope,
                                     # change in x over change in y
                                     (col - 0.5) / (row + 0.5),
                                     m_x, m_y, m_xy)

            else:
                if in_blocking:
                    in_blocking = False

                    # restrict current scan to the left side of current cell for
                    # future rows -- change in x over change in y
                    l_slope = (col - 0.5) / (row - 0.5)

            if not m_xy:
                cell += m_x
            else:
                cell += m_x * w

            col += 1

        # if the row ends in a blocking cell, this scan is finished.
        if in_blocking:
            return

        row += 1


def compute_fov(blocking: List[bool], w: int, h: int,
                src_x: int, src_y: int, distance: int) -> List[bool]:
    """Allocate a fresh flat FOV array and fill it from (src_x, src_y)."""
    fov = [False] * (w * h)
    cast_shadow(src_x, src_y, w, fov, blocking, distance)
    return fov
