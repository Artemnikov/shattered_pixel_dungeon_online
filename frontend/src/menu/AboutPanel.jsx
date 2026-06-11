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
import Panel from './Panel';
import { APP_VERSION } from './content/changelog';

export default function AboutPanel({ onClose }) {
  return (
    <Panel title="About" icon="SHPX" onClose={onClose}>
      <div className="opd-about">
        <p className="opd-about-title">Online Pixel Dungeon</p>
        <p className="opd-about-version">v{APP_VERSION}</p>
        <p>
          An online, real-time multiplayer remake inspired by{' '}
          <strong>Shattered Pixel Dungeon</strong> by Evan Debenham, itself based on
          the original <strong>Pixel Dungeon</strong> by Oleg Dolya.
        </p>
        <p>
          Art, audio and the title-screen design are from Shattered Pixel Dungeon,
          which is free software released under the GPLv3.
        </p>
        <p className="opd-about-links">
          <a href="https://shatteredpixel.com" target="_blank" rel="noreferrer">shatteredpixel.com</a>
          {' · '}
          <a href="https://patreon.com/ShatteredPixel" target="_blank" rel="noreferrer">Support Evan on Patreon</a>
          {' · '}
          <a href="https://github.com/00-Evan/shattered-pixel-dungeon" target="_blank" rel="noreferrer">SPD Source (GPLv3)</a>
        </p>
        <p className="opd-about-copy">© 2026 ArtemNikov — <a href="https://github.com/Artemnikov/shattered_pixel_dungeon_online" target="_blank" rel="noreferrer">Online Pixel Dungeon</a></p>
      </div>
    </Panel>
  );
}
