import { useEffect, useRef } from 'react';
import AudioManager from '../audio/AudioManager';
import itemsSpriteSrc from '../assets/pixel-dungeon/sprites/items.png';
import toolbarSpriteSrc from '../assets/pixel-dungeon/interfaces/toolbar.png';
import { getItemSpriteCoords } from '../rendering/sprites';

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
  onWait,
  onSearch,
  onInventory,
  onSlotClick,
  onSlotDoubleClick,
}) {
  const canvasRef = useRef(null);
  const areasRef = useRef(makeButtonAreas());
  const imgsRef = useRef({ toolbar: null, items: null });
  const imgsLoaded = useRef(false);
  const animFrame = useRef(null);

  useEffect(() => {
    const toolbarImg = new Image();
    const itemsImg = new Image();
    let loaded = 0;
    const check = () => { if (++loaded >= 2) imgsLoaded.current = true; };
    toolbarImg.onload = check;
    itemsImg.onload = check;
    toolbarImg.src = toolbarSpriteSrc;
    itemsImg.src = itemsSpriteSrc;
    if (toolbarImg.complete && toolbarImg.naturalWidth > 0) check();
    if (itemsImg.complete && itemsImg.naturalWidth > 0) check();
    imgsRef.current = { toolbar: toolbarImg, items: itemsImg };
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const quickslotsToShow = 4 +
      (canvasWidth > 152 * (3 / S) ? 1 : 0) +
      (canvasWidth > 170 * (3 / S) ? 1 : 0);

    const startingSlot = quickSwapper && quickslotsToShow < 6 ? 0 : 0;
    const endingSlot = quickSwapper && quickslotsToShow < 6
      ? 2 : Math.min(startingSlot + quickslotsToShow - 1, 5);
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

    const timer = requestAnimationFrame(() => render());
    animFrame.current = timer;
    return () => cancelAnimationFrame(timer);

    function render() {
      const ctx = canvas.getContext('2d');
      const ti = imgsRef.current.toolbar;
      const ii = imgsRef.current.items;
      if (!ti || !ii || !ti.complete || !ii.complete) return;

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

      function drawItemSprite(item, dx, dy, slotW, slotH, borderL, borderR) {
        if (!item || !ii.complete) return;
        const coords = getItemSpriteCoords(item.name, item.type);
        if (!coords) return;
        const is = 16 * S;
        const padL = borderL * S;
        const padR = borderR * S;
        const availW = slotW - padL - padR;
        const availH = slotH;
        const ix = dx + padL + (availW - is) / 2;
        const iy = dy + (availH - is) / 2;
        ctx.drawImage(ii, coords[0] * 16, coords[1] * 16, 16, 16, ix, iy, is, is);
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
  }, [mode, interfaceSize, flipToolbar, quickSwapper, canvasWidth, items, equippedItems, targetingMode]);

  const handleClick = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
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
      style={{ imageRendering: 'pixelated', display: 'block' }}
    />
  );
}
