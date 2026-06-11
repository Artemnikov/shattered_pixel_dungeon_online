// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
// See the GNU General Public License for more details.
//
import { useEffect, useRef } from 'react';
import AudioManager from '../audio/AudioManager';
import itemsSpriteSrc from '../assets/pixel-dungeon/sprites/items.png';
import toolbarSpriteSrc from '../assets/pixel-dungeon/interfaces/toolbar.png';
import iconsSpriteSrc from '../assets/pixel-dungeon/interfaces/icons.png';
import { coordsForItem } from '../rendering/sprites';
import { itemRects } from '../rendering/spriteRects';

const S = 3;

const BTN_INVENTORY = { x: 0, y: 0, w: 24, h: 26, iconX: 160, iconY: 0, iconW: 16, iconH: 16 };
const BTN_WAIT      = { x: 24, y: 0, w: 20, h: 26, iconX: 176, iconY: 0, iconW: 16, iconH: 16 };
const BTN_SEARCH    = { x: 44, y: 0, w: 20, h: 26, iconX: 192, iconY: 0, iconW: 16, iconH: 16 };
const QS_START      = { x: 86,  y: 0, w: 20, h: 24, borderL: 2, borderR: 1 };
const QS_MID        = { x: 88,  y: 0, w: 18, h: 24, borderL: 0, borderR: 1 };
const QS_END        = { x: 106, y: 0, w: 19, h: 24, borderL: 0, borderR: 2 };
const SWAP_BTN      = { x: 128, y: 0, w: 21, h: 23 };

const TOOL_PAD = 2;

function makeButtonAreas() {
  return { wait: null, search: null, inventory: null, quickslots: [], swap: null };
}

export default function Toolbar({
  mode = 'split',
  interfaceSize = 0,
  flipToolbar = false,
  quickSwapper = false,
  canvasWidth = 200,
  items = [],
  equippedItems = {},
  targetingMode = false,
  swappedQuickslots = false,
  onWait,
  onSearch,
  onInventory,
  onQuickBag,
  onSlotClick,
  onSlotDoubleClick,
  onSwap,
}) {
  const canvasRef = useRef(null);
  const areasRef = useRef(makeButtonAreas());
  const imgsRef = useRef({ toolbar: null, items: null, icons: null });
  const imgsLoaded = useRef(false);
  const animFrame = useRef(null);
  const touchTimerRef = useRef(null);
  const longPressFiredRef = useRef(false);

  useEffect(() => {
    const toolbarImg = new Image();
    const itemsImg = new Image();
    const iconsImg = new Image();
    let loaded = 0;
    const check = () => { if (++loaded >= 3) imgsLoaded.current = true; };
    toolbarImg.onload = check;
    itemsImg.onload = check;
    iconsImg.onload = check;
    toolbarImg.src = toolbarSpriteSrc;
    itemsImg.src = itemsSpriteSrc;
    iconsImg.src = iconsSpriteSrc;
    if (toolbarImg.complete && toolbarImg.naturalWidth > 0) check();
    if (itemsImg.complete && itemsImg.naturalWidth > 0) check();
    if (iconsImg.complete && iconsImg.naturalWidth > 0) check();
    imgsRef.current = { toolbar: toolbarImg, items: itemsImg, icons: iconsImg };
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const quickslotsToShow = 4 +
      (canvasWidth > 152 * S ? 1 : 0) +
      (canvasWidth > 170 * S ? 1 : 0);

    const startingSlot = quickSwapper && quickslotsToShow < 6
      ? (swappedQuickslots ? 3 : 0) : 0;
    const endingSlot = quickSwapper && quickslotsToShow < 6
      ? startingSlot + 2 : Math.min(startingSlot + quickslotsToShow - 1, 5);
    const finalQuickslots = endingSlot - startingSlot + 1;
    const showSwap = quickSwapper && quickslotsToShow < 6;

    const btnW = BTN_INVENTORY.w + TOOL_PAD;
    const btnH = BTN_INVENTORY.h + TOOL_PAD;

    const qsWidths = [];
    for (let i = startingSlot; i <= endingSlot; i++) {
      const isStart = (i === startingSlot && !flipToolbar) || (i === endingSlot && flipToolbar);
      const isEnd = (i === endingSlot && !flipToolbar) || (i === startingSlot && flipToolbar);
      const spec = isEnd ? QS_END : isStart ? QS_START : QS_MID;
      qsWidths.push(spec.w + TOOL_PAD);
    }
    const totalQsW = qsWidths.reduce((a, b) => a + b, 0);

    let totalW;
    if (interfaceSize > 0) {
      totalW = btnW * 3 + totalQsW + TOOL_PAD;
    } else {
      const waitW = BTN_WAIT.w + TOOL_PAD;
      const searchW = BTN_SEARCH.w + TOOL_PAD;
      totalW = waitW + searchW + btnW + totalQsW + TOOL_PAD;
    }
    if (showSwap) totalW += SWAP_BTN.w + TOOL_PAD;

    const height = (BTN_INVENTORY.h + TOOL_PAD) * S;
    canvas.width = Math.ceil(totalW) * S;
    canvas.height = height;

    animFrame.current = requestAnimationFrame(render);
    return () => cancelAnimationFrame(animFrame.current);

    function render() {
      const ctx = canvas.getContext('2d');
      const ti = imgsRef.current.toolbar;
      const ii = imgsRef.current.items;
      const ici = imgsRef.current.icons;
      if (!ti || !ii || !ici || !ti.complete || !ii.complete || !ici.complete) {
        animFrame.current = requestAnimationFrame(render);
        return;
      }

      ctx.imageSmoothingEnabled = false;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const areas = makeButtonAreas();
      const yOff = TOOL_PAD * S;

      function drawTool(spec, dx, dy, dw, dh) {
        if (!ti.complete) return;
        ctx.drawImage(ti, spec.x, spec.y, spec.w, spec.h, dx, dy, dw, dh);
      }

      function drawIcon(spec, dx, dy) {
        if (!ti.complete) return;
        const iw = spec.iconW * S;
        const ih = spec.iconH * S;
        const cx = dx + (spec.w * S - iw) / 2;
        const cy = dy + (spec.h * S - ih) / 2;
        ctx.drawImage(ti, spec.iconX, spec.iconY, spec.iconW, spec.iconH, cx, cy, iw, ih);
      }

      function drawQuickslotFrame(slotIdx, dx, dy, dw, dh) {
        const isStart = (slotIdx === startingSlot && !flipToolbar) || (slotIdx === endingSlot && flipToolbar);
        const isEnd = (slotIdx === endingSlot && !flipToolbar) || (slotIdx === startingSlot && flipToolbar);
        const spec = isEnd ? QS_END : isStart ? QS_START : QS_MID;
        drawTool(spec, dx, dy, dw, dh);
        return spec;
      }

      function drawSwapPreview(btnArea) {
        if (!ii?.complete || !ici?.complete) return;
        const tiny = 7;

        // Determine preview slots matching SPD's SlotSwapTool slot order
        let previewSlots;
        if (flipToolbar) {
          previewSlots = swappedQuickslots ? [0, 1, 2] : [3, 4, 5];
        } else {
          previewSlots = swappedQuickslots ? [2, 1, 0] : [5, 4, 3];
        }

        // Draw CHANGES arrow from icons.png at (85,0,15,15)
        const cx = (btnArea.x + 2) * sc;
        const cy = (btnArea.y + 3) * sc;
        ctx.drawImage(ici, 85, 0, 15, 15, cx, cy, tiny * sc, tiny * sc);

        // Draw 3 item previews (icons[1-3] in SPD)
        const previewPos = [
          { x: 11, y: 3 },
          { x: 2, y: 13 },
          { x: 11, y: 13 },
        ];

        for (let i = 0; i < 3; i++) {
          const item = items[previewSlots[i]];
          if (!item) continue;
          const coords = coordsForItem(item);
          if (!coords) continue;
          const rect = itemRects.get(coords[0], coords[1]);
          const rx = rect ? rect.rx : 0;
          const ry = rect ? rect.ry : 0;
          const sw = rect ? Math.min(rect.w, tiny) : tiny;
          const sh = rect ? Math.min(rect.h, tiny) : tiny;
          const px = (btnArea.x + previewPos[i].x) * sc;
          const py = (btnArea.y + previewPos[i].y) * sc;
          ctx.drawImage(ii, coords[0] * 16 + rx, coords[1] * 16 + ry, sw, sh, px, py, sw * sc, sh * sc);
        }
      }

      function drawItemSprite(item, dx, dy, slotW, slotH, borderL, borderR) {
        if (!item || !ii.complete) return;
        const coords = coordsForItem(item);
        if (!coords) return;
        // Crop to the art's measured rect (top-left anchored in its cell, like
        // SPD) and centre that, so sprites aren't skewed toward the top-left.
        const rect = itemRects.get(coords[0], coords[1]);
        const rx = rect ? rect.rx : 0;
        const ry = rect ? rect.ry : 0;
        const sw = rect ? rect.w : 16;
        const sh = rect ? rect.h : 16;
        const padL = borderL * S;
        const padR = borderR * S;
        const availW = slotW - padL - padR;
        const availH = slotH;
        const ix = dx + padL + (availW - sw * S) / 2;
        const iy = dy + (availH - sh * S) / 2;
        ctx.drawImage(ii, coords[0] * 16 + rx, coords[1] * 16 + ry, sw, sh, ix, iy, sw * S, sh * S);
      }

      const sc = S;

      if (interfaceSize > 0) {
        let right = canvas.width / sc;
        const invBtn = BTN_INVENTORY;
        const waitBtn = BTN_WAIT;
        const searchBtn = BTN_SEARCH;

        areas.inventory = { x: right - invBtn.w, y: 0, w: invBtn.w, h: invBtn.h };
        right = right - invBtn.w - TOOL_PAD;
        areas.wait = { x: right - waitBtn.w, y: 0, w: waitBtn.w, h: waitBtn.h };
        right = right - waitBtn.w - TOOL_PAD;
        areas.search = { x: right - searchBtn.w, y: 0, w: searchBtn.w, h: searchBtn.h };
        right = right - searchBtn.w - TOOL_PAD;

        for (let i = endingSlot; i >= startingSlot; i--) {
          const qsSpec = QS_END;
          const qw = qsSpec.w;
          right = right - qw;
          areas.quickslots[i - startingSlot] = { x: right, y: 2, w: qw, h: 24 };
          right -= TOOL_PAD;
        }

        drawTool(invBtn, areas.inventory.x * sc, yOff, invBtn.w * sc, invBtn.h * sc);
        drawIcon(invBtn, areas.inventory.x * sc, yOff);
        drawTool(waitBtn, areas.wait.x * sc, yOff, waitBtn.w * sc, waitBtn.h * sc);
        drawIcon(waitBtn, areas.wait.x * sc, yOff);
        drawTool(searchBtn, areas.search.x * sc, yOff, searchBtn.w * sc, searchBtn.h * sc);
        drawIcon(searchBtn, areas.search.x * sc, yOff);

        for (let i = endingSlot; i >= startingSlot; i--) {
          const qIdx = i - startingSlot;
          const a = areas.quickslots[qIdx];
          const spec = drawQuickslotFrame(i, a.x * sc, yOff + a.y * sc, a.w * sc, a.h * sc);
          drawItemSprite(items[i], a.x * sc, yOff + a.y * sc, a.w * sc, a.h * sc, spec.borderL, spec.borderR);
        }
      } else {
        let right = canvas.width / sc;

        if (mode === 'split') {
          areas.wait = { x: 0, y: 0, w: BTN_WAIT.w, h: BTN_WAIT.h };
          areas.search = { x: BTN_WAIT.w + TOOL_PAD, y: 0, w: BTN_SEARCH.w, h: BTN_SEARCH.h };
          areas.inventory = { x: right - BTN_INVENTORY.w, y: 0, w: BTN_INVENTORY.w, h: BTN_INVENTORY.h };
          right = right - BTN_INVENTORY.w - TOOL_PAD;

          for (let i = startingSlot; i <= endingSlot; i++) {
            const spec = (i === endingSlot) ? QS_END : (i === startingSlot) ? QS_START : QS_MID;
            if (i === startingSlot) {
              areas.quickslots[0] = { x: right - spec.w, y: 2, w: spec.w, h: 24 };
            } else {
              const prev = areas.quickslots[i - startingSlot - 1];
              areas.quickslots[i - startingSlot] = { x: prev.x - spec.w - TOOL_PAD, y: 2, w: spec.w, h: 24 };
            }
            right = areas.quickslots[i - startingSlot].x;
          }

          const leftEdge = (areas.search?.x ?? 0) + (areas.search?.w ?? 0) + TOOL_PAD;
          const rightEdge = areas.quickslots.length > 0 ? areas.quickslots[areas.quickslots.length - 1].x : right;
          let shift = leftEdge - rightEdge;
          if (shift > 0) {
            shift = Math.round(shift / 2);
            areas.quickslots.forEach(a => { a.x += shift; });
          }

          if (showSwap) {
            const lastQs = areas.quickslots[areas.quickslots.length - 1];
            areas.swap = { x: lastQs.x - SWAP_BTN.w - TOOL_PAD, y: 3, w: SWAP_BTN.w, h: SWAP_BTN.h };
          }

          drawTool(BTN_WAIT, areas.wait.x * sc, yOff, areas.wait.w * sc, areas.wait.h * sc);
          drawIcon(BTN_WAIT, areas.wait.x * sc, yOff);
          drawTool(BTN_SEARCH, areas.search.x * sc, yOff, areas.search.w * sc, areas.search.h * sc);
          drawIcon(BTN_SEARCH, areas.search.x * sc, yOff);
          drawTool(BTN_INVENTORY, areas.inventory.x * sc, yOff, areas.inventory.w * sc, areas.inventory.h * sc);
          drawIcon(BTN_INVENTORY, areas.inventory.x * sc, yOff);

          areas.quickslots.forEach((a, idx) => {
            const spec = drawQuickslotFrame(startingSlot + idx, a.x * sc, yOff + a.y * sc, a.w * sc, a.h * sc);
            drawItemSprite(items[startingSlot + idx], a.x * sc, yOff + a.y * sc, a.w * sc, a.h * sc, spec.borderL, spec.borderR);
          });

          if (showSwap && areas.swap) {
            drawTool(SWAP_BTN, areas.swap.x * sc, yOff + areas.swap.y * sc, areas.swap.w * sc, areas.swap.h * sc);
            drawSwapPreview(areas.swap);
          }
        } else {
          const toolbarW = (BTN_WAIT.w + TOOL_PAD) + (BTN_SEARCH.w + TOOL_PAD) + (BTN_INVENTORY.w + TOOL_PAD) + totalQsW + (showSwap ? SWAP_BTN.w + TOOL_PAD : 0);

          if (mode === 'center') {
            right = (canvas.width / sc + toolbarW) / 2;
          }

          areas.wait = { x: right - BTN_WAIT.w, y: 0, w: BTN_WAIT.w, h: BTN_WAIT.h };
          right = right - BTN_WAIT.w - TOOL_PAD;
          areas.search = { x: right - BTN_SEARCH.w, y: 0, w: BTN_SEARCH.w, h: BTN_SEARCH.h };
          right = right - BTN_SEARCH.w - TOOL_PAD;
          areas.inventory = { x: right - BTN_INVENTORY.w, y: 0, w: BTN_INVENTORY.w, h: BTN_INVENTORY.h };
          right = right - BTN_INVENTORY.w - TOOL_PAD;

          for (let i = startingSlot; i <= endingSlot; i++) {
            const spec = (i === endingSlot) ? QS_END : (i === startingSlot) ? QS_START : QS_MID;
            if (i === startingSlot) {
              areas.quickslots[0] = { x: right - spec.w, y: 2, w: spec.w, h: 24 };
            } else {
              const prev = areas.quickslots[i - startingSlot - 1];
              areas.quickslots[i - startingSlot] = { x: prev.x - spec.w - TOOL_PAD, y: 2, w: spec.w, h: 24 };
            }
            right = areas.quickslots[i - startingSlot].x;
          }

          if (showSwap) {
            const lastQs = areas.quickslots[areas.quickslots.length - 1];
            areas.swap = { x: lastQs.x - SWAP_BTN.w - TOOL_PAD, y: 3, w: SWAP_BTN.w, h: SWAP_BTN.h };
          }

          drawTool(BTN_WAIT, areas.wait.x * sc, yOff, areas.wait.w * sc, areas.wait.h * sc);
          drawIcon(BTN_WAIT, areas.wait.x * sc, yOff);
          drawTool(BTN_SEARCH, areas.search.x * sc, yOff, areas.search.w * sc, areas.search.h * sc);
          drawIcon(BTN_SEARCH, areas.search.x * sc, yOff);
          drawTool(BTN_INVENTORY, areas.inventory.x * sc, yOff, areas.inventory.w * sc, areas.inventory.h * sc);
          drawIcon(BTN_INVENTORY, areas.inventory.x * sc, yOff);

          areas.quickslots.forEach((a, idx) => {
            const spec = drawQuickslotFrame(startingSlot + idx, a.x * sc, yOff + a.y * sc, a.w * sc, a.h * sc);
            drawItemSprite(items[startingSlot + idx], a.x * sc, yOff + a.y * sc, a.w * sc, a.h * sc, spec.borderL, spec.borderR);
          });

          if (showSwap && areas.swap) {
            drawTool(SWAP_BTN, areas.swap.x * sc, yOff + areas.swap.y * sc, areas.swap.w * sc, areas.swap.h * sc);
            drawSwapPreview(areas.swap);
          }
        }

        if (flipToolbar) {
          const cw = canvas.width / sc;
          const flip = (a) => ({ x: cw - a.x - a.w, y: a.y, w: a.w, h: a.h });
          if (areas.wait) areas.wait = flip(areas.wait);
          if (areas.search) areas.search = flip(areas.search);
          if (areas.inventory) areas.inventory = flip(areas.inventory);
          areas.quickslots = areas.quickslots.map(flip);
          if (areas.swap) areas.swap = flip(areas.swap);
        }
      }

      areasRef.current = areas;
    }
  }, [mode, interfaceSize, flipToolbar, quickSwapper, swappedQuickslots, canvasWidth, items, equippedItems, targetingMode]);

  const handlePointerDown = (e) => {
    if (e.pointerType !== 'touch' || !onQuickBag) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) / S;
    const my = (e.clientY - rect.top) / S;
    const areas = areasRef.current;

    function hit(a) { return a && mx >= a.x && mx <= a.x + a.w && my >= a.y && my <= a.y + a.h; }

    if (hit(areas.inventory)) {
      longPressFiredRef.current = false;
      touchTimerRef.current = setTimeout(() => {
        longPressFiredRef.current = true;
        AudioManager.play('CLICK');
        if (onQuickBag) onQuickBag();
      }, 500);
    }
  };

  const handlePointerUp = () => {
    clearTimeout(touchTimerRef.current);
  };

  const handleClick = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    if (longPressFiredRef.current) { longPressFiredRef.current = false; return; }
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) / S;
    const my = (e.clientY - rect.top) / S;
    const areas = areasRef.current;

    function hit(a) { return a && mx >= a.x && mx <= a.x + a.w && my >= a.y && my <= a.y + a.h; }

    if (hit(areas.wait)) {
      AudioManager.play('CLICK');
      if (onWait) onWait();
      return;
    }
    if (hit(areas.search)) {
      AudioManager.play('CLICK');
      if (onSearch) onSearch();
      return;
    }
    if (hit(areas.inventory)) {
      AudioManager.play('CLICK');
      if (onInventory) onInventory();
      return;
    }
    if (hit(areas.swap)) {
      AudioManager.play('CLICK');
      if (onSwap) onSwap();
      return;
    }
    for (let i = 0; i < areas.quickslots.length; i++) {
      if (hit(areas.quickslots[i])) {
        AudioManager.play('CLICK');
        const itemIdx = i;
        const item = items[itemIdx];
        if (onSlotClick) onSlotClick(item, itemIdx);
        return;
      }
    }
  };

  const handleDoubleClick = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) / S;
    const my = (e.clientY - rect.top) / S;
    const areas = areasRef.current;

    function hit(a) { return a && mx >= a.x && mx <= a.x + a.w && my >= a.y && my <= a.y + a.h; }

    for (let i = 0; i < areas.quickslots.length; i++) {
      if (hit(areas.quickslots[i])) {
        const item = items[i];
        if (onSlotDoubleClick) onSlotDoubleClick(item, i);
        return;
      }
    }
  };

  return (
    <canvas
      ref={canvasRef}
      className="toolbar-canvas"
      onClick={handleClick}
      onDoubleClick={handleDoubleClick}
      onPointerDown={handlePointerDown}
      onPointerUp={handlePointerUp}
      onPointerLeave={handlePointerUp}
      onPointerCancel={handlePointerUp}
      style={{ imageRendering: 'pixelated', display: 'block' }}
    />
  );
}
