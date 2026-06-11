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
// Port of Shattered Pixel Dungeon's TitleBackground.java parallax system to
// Canvas2D. A back→front stack of layers, each made of sprite-sheet frames that
// scroll upward and recycle to the bottom once they leave the screen, giving the
// title screen its slow drifting-cavern look.
//
// Source of truth: core/.../ui/TitleBackground.java (SCROLL_SPEED=15, scale=h/450,
// per-layer shift multipliers and brightnesses).

import archsUrl from '../assets/pixel-dungeon/splashes/title/archs.png';
import backClustersUrl from '../assets/pixel-dungeon/splashes/title/back_clusters.png';
import midMixedUrl from '../assets/pixel-dungeon/splashes/title/mid_mixed.png';
import frontSmallUrl from '../assets/pixel-dungeon/splashes/title/front_small.png';

export const TITLE_ASSET_URLS = [archsUrl, backClustersUrl, midMixedUrl, frontSmallUrl];

const SCROLL_SPEED = 15;

// frame dimensions / sheet column counts (sheets are laid out row-major)
const FILMS = {
  arch:    { url: archsUrl,        fw: 333, fh: 100, cols: 3, count: 6 },
  cluster: { url: backClustersUrl, fw: 450, fh: 250, cols: 1, count: 2 },
  small:   { url: frontSmallUrl,   fw: 112, fh: 116, cols: 9, count: 20 },
  mid:     { url: midMixedUrl,     fw: 273, fh: 242, cols: 7, count: 24 },
};

const randFloat = (min, max) => min + Math.random() * (max - min);
const randInt = (min, max) => Math.floor(randFloat(min, max + 1));

function frameRect(film, i) {
  const col = i % film.cols;
  const row = Math.floor(i / film.cols);
  return { sx: col * film.fw, sy: row * film.fh, sw: film.fw, sh: film.fh };
}

// weighted-ish frame picker that avoids recently used frames (mirrors the
// getXFrame() helpers in the original without the exact chance bookkeeping)
function makePicker(count, memory) {
  const recent = [];
  return () => {
    let i;
    let guard = 0;
    do {
      i = randInt(0, count - 1);
      guard++;
    } while (recent.includes(i) && guard < 20);
    recent.unshift(i);
    if (recent.length > Math.min(memory, count - 1)) recent.pop();
    return i;
  };
}

export default class TitleParallax {
  // images: { [url]: HTMLImageElement }
  constructor(images) {
    this.images = images;
    this.width = 0;
    this.height = 0;
    this.archPick = makePicker(FILMS.arch.count, 0);
    this.clusterPick = makePicker(FILMS.cluster.count, 0);
    this.midPick = makePicker(FILMS.mid.count, 19);
    this.smallPick = makePicker(FILMS.small.count, 14);
    this.reset(0, 0);
  }

  reset(width, height) {
    this.width = width;
    this.height = height;
    this.archs = [];
    this.layers = {
      clustersFar: [],
      clusters: [],
      smallFars: [],
      mids1: [],
      mids2: [],
      smallCloses: [],
    };
    this._primed = false;
  }

  // Run several large update steps so the screen starts full of objects
  // instead of empty (the original persists layers across scene resets).
  prime() {
    if (this._primed || this.width === 0) return;
    for (let i = 0; i < 60; i++) this.update(0.1);
    this._primed = true;
  }

  get scale() {
    return this.height / 450;
  }

  update(dt) {
    if (this.width === 0 || this.height === 0) return;
    const portrait = this.width <= this.height;
    let scale = this.scale;
    let shift = dt * SCROLL_SPEED * scale;
    if (portrait) shift /= 1.5;

    this.updateArchLayer(scale, shift);

    if (portrait) scale /= 1.5;

    // density: spacing control, pulled 1/3 toward 1 when beyond it
    let density = this.width / (800 * scale);
    density = (density + 0.5) / 1.5;
    this.density = density;

    shift *= 1.33; this.updateFloating(this.layers.clustersFar, {
      film: FILMS.cluster, scale, scaleRange: [0.5, 0.5], brightness: 0.5,
      xMode: 'center', spacingMul: 0.5, yFull: true, padBase: 300, pick: this.clusterPick, shift, density });
    shift *= 1.5; this.updateFloating(this.layers.clusters, {
      film: FILMS.cluster, scale, scaleRange: [1, 1], brightness: 0.75,
      xMode: 'center', spacingMul: 0.5, yFull: true, padBase: 300, pick: this.clusterPick, shift, density });
    shift *= 1.33; this.updateFloating(this.layers.smallFars, {
      film: FILMS.small, scale, scaleRange: [0.75, 1.25], brightness: 0.8,
      xMode: 'small', spacingMul: 1.0, yFull: false, padBase: 150, pick: this.smallPick, shift, density });
    shift *= 1.33; this.updateFloating(this.layers.mids1, {
      film: FILMS.mid, scale, scaleRange: [0.75, 1.25], brightness: 0.9,
      xMode: 'center', spacingMul: 0.75, yFull: true, padBase: 300, pick: this.midPick, shift, density });
    shift *= 1.33; this.updateFloating(this.layers.mids2, {
      film: FILMS.mid, scale, scaleRange: [1.25, 1.75], brightness: 1.0,
      xMode: 'center', spacingMul: 0.75, yFull: true, padBase: 300, pick: this.midPick, shift, density });
    shift *= 1.33; this.updateFloating(this.layers.smallCloses, {
      film: FILMS.small, scale, scaleRange: [2.0, 2.5], brightness: 1.0,
      xMode: 'center', spacingMul: 1.0, yFull: true, padBase: 150, pick: this.smallPick, shift, density });
  }

  updateArchLayer(scale, shift) {
    const film = FILMS.arch;
    const archW = film.fw * scale;
    const archH = film.fh * scale;
    let bottom = 0;
    const toMove = [];
    for (const a of this.archs) {
      a.y -= shift;
      if (a.y + archH < 0) toMove.push(a);
      else if (a.y + archH > bottom) bottom = a.y + archH;
    }
    if (toMove.length) {
      for (const a of toMove) { a.frame = this.archPick(); a.y = bottom - 5 * scale; }
      bottom += archH;
    }
    while (bottom < this.height) {
      let left = -5 + (-33.334 * randInt(1, 9) * scale);
      while (left < this.width) {
        this.archs.push({ frame: this.archPick(), x: left, y: bottom - 5 * scale, scale, angle: 0 });
        left += archW - (9 * scale);
      }
      bottom += archH;
    }
  }

  updateFloating(list, o) {
    const { film, shift, density } = o;
    let bottom = 0;
    let lastX = 0;
    const toMove = [];
    for (const s of list) {
      s.y -= shift;
      const h = film.fh * s.scale;
      if (s.y + h < -20) toMove.push(s);
      else if (s.y + h > bottom) { bottom = s.y + h; lastX = s.x; }
    }
    const placeX = (w) => {
      let x, flex = 0;
      do {
        if (o.xMode === 'small') x = randFloat(w / 3, this.width - 4 * w / 3);
        else x = randFloat(-w / 3, this.width - 2 * w / 3);
        flex += 1;
      } while (Math.abs(x - lastX) < density * (w * o.spacingMul - flex));
      return x;
    };
    if (toMove.length) {
      for (const s of toMove) {
        s.frame = o.pick();
        s.scale = o.scale * randFloat(o.scaleRange[0], o.scaleRange[1]);
        const w = film.fw * s.scale, h = film.fh * s.scale;
        s.x = placeX(w);
        const base = o.yFull ? bottom - h : bottom - h / 2;
        s.y = base + randFloat(h / 2, h) / density;
        s.angle = randFloat(-20, 20);
        bottom = s.y + h; lastX = s.x;
      }
    }
    const padding = o.padBase - (o.padBase / 2 / density);
    while (bottom < this.height + padding) {
      const sc = o.scale * randFloat(o.scaleRange[0], o.scaleRange[1]);
      const w = film.fw * sc, h = film.fh * sc;
      const x = placeX(w);
      const base = o.yFull ? bottom - h : bottom - h / 2;
      const y = base + randFloat(h / 2, h) / density;
      const s = { frame: o.pick(), x, y, scale: sc, angle: randFloat(-20, 20), brightness: o.brightness };
      list.push(s);
      bottom = y + h; lastX = x;
    }
  }

  draw(ctx) {
    const drawLayer = (list, film, brightness) => {
      ctx.filter = brightness < 1 ? `brightness(${brightness})` : 'none';
      const img = this.images[film.url];
      if (!img) return;
      for (const s of list) {
        const { sx, sy, sw, sh } = frameRect(film, s.frame);
        const w = sw * s.scale, h = sh * s.scale;
        ctx.save();
        ctx.translate(s.x + w / 2, s.y + h / 2);
        if (s.angle) ctx.rotate((s.angle * Math.PI) / 180);
        ctx.drawImage(img, sx, sy, sw, sh, -w / 2, -h / 2, w, h);
        ctx.restore();
      }
    };

    // back → front
    drawLayer(this.archs, FILMS.arch, 1.0);

    // subtle vertical darkening over the back layer
    const grad = ctx.createLinearGradient(0, 0, 0, this.height);
    grad.addColorStop(0, 'rgba(0,0,0,0)');
    grad.addColorStop(1, 'rgba(0,0,0,0.53)');
    ctx.filter = 'none';
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, this.width, this.height);

    drawLayer(this.layers.clustersFar, FILMS.cluster, 0.5);
    drawLayer(this.layers.clusters, FILMS.cluster, 0.75);
    drawLayer(this.layers.smallFars, FILMS.small, 0.8);
    drawLayer(this.layers.mids1, FILMS.mid, 0.9);
    drawLayer(this.layers.mids2, FILMS.mid, 1.0);
    drawLayer(this.layers.smallCloses, FILMS.small, 1.0);
    ctx.filter = 'none';
  }
}
