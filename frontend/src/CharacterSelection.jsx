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
// "Choose Your Hero" screen — a faithful re-implementation of Shattered Pixel
// Dungeon's HeroSelectScene: the selected class's splash-art banner fills the
// background with left/right vignette fades, a row of small pixel class busts
// (cropped at frame 0,90,12,15 of each hero sprite sheet) lets you pick, and the
// hero's name + original short description show in the left UI column. The
// remake-specific difficulty + name controls are kept in the same column.
import { useEffect, useRef, useState } from 'react';
import './heroSelect.css';
import AudioManager from './audio/AudioManager';
import Icon from './menu/Icon';
import { effectiveMusicVolume, subscribe } from './menu/menuSettings';

import themeMusic from './assets/pixel-dungeon/themes/theme_1.ogg';
import descendSound from './assets/pixel-dungeon/audio/descend.mp3';

import warriorSplash from './assets/pixel-dungeon/splashes/warrior.jpg';
import mageSplash from './assets/pixel-dungeon/splashes/mage.jpg';
import rogueSplash from './assets/pixel-dungeon/splashes/rogue.jpg';
import huntressSplash from './assets/pixel-dungeon/splashes/huntress.jpg';

import warriorSheet from './assets/pixel-dungeon/sprites/warrior.png';
import mageSheet from './assets/pixel-dungeon/sprites/mage.png';
import rogueSheet from './assets/pixel-dungeon/sprites/rogue.png';
import huntressSheet from './assets/pixel-dungeon/sprites/huntress.png';

// class bust frame within the 256x128 hero sprite sheet (from HeroSelectScene.HeroBtn)
const HERO_FRAME = { x: 0, y: 90, w: 12, h: 15 };
const SHEET_W = 256, SHEET_H = 128;

const HEROES = [
  {
    id: 'warrior', name: 'Warrior', sheet: warriorSheet, splash: warriorSplash,
    desc: 'The Warrior endures extra damage with shielding granted by his broken seal. The seal can be moved between armors and transfers a single upgrade.',
  },
  {
    id: 'mage', name: 'Mage', sheet: mageSheet, splash: mageSplash,
    desc: "The Mage is an arcane expert and carries a magical staff that's stronger than a wand. The staff can be imbued with any wand the Mage finds.",
  },
  {
    id: 'rogue', name: 'Rogue', sheet: rogueSheet, splash: rogueSplash,
    desc: 'The Rogue can evade enemies and strike from invisibility using his cloak of shadows. He also detects secrets and traps from a greater distance.',
  },
  {
    id: 'huntress', name: 'Huntress', sheet: huntressSheet, splash: huntressSplash,
    desc: 'The Huntress is a master of thrown weapons and has a magical bow with infinite arrows. She also travels through tall grass without trampling it.',
  },
];

function HeroBust({ sheet, scale = 3, selected }) {
  const f = HERO_FRAME;
  return (
    <span
      className="hero-bust"
      style={{
        width: f.w * scale,
        height: f.h * scale,
        backgroundImage: `url(${sheet})`,
        backgroundRepeat: 'no-repeat',
        backgroundSize: `${SHEET_W * scale}px ${SHEET_H * scale}px`,
        backgroundPosition: `-${f.x * scale}px -${f.y * scale}px`,
        imageRendering: 'pixelated',
        filter: selected ? 'none' : 'brightness(0.6)',
      }}
    />
  );
}

const CharacterSelection = ({ onSelect }) => {
  const [selectedClass, setSelectedClass] = useState('warrior');
  const [difficulty, setDifficulty] = useState('normal');
  const [strongerBosses, setStrongerBosses] = useState(false);
  const [playerName, setPlayerName] = useState('');
  const [landscape, setLandscape] = useState(
    typeof window !== 'undefined' ? window.innerWidth > window.innerHeight : true
  );
  const audioRef = useRef(null);

  const hero = HEROES.find(h => h.id === selectedClass) || HEROES[0];

  useEffect(() => {
    const onResize = () => setLandscape(window.innerWidth > window.innerHeight);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  // theme music (loops; volume from settings) — carried over from the previous screen
  useEffect(() => {
    const audio = new Audio(themeMusic);
    audio.loop = true;
    audio.volume = effectiveMusicVolume();
    audioRef.current = audio;

    const tryPlay = () => { audio.play().catch(() => {}); };
    tryPlay();
    document.addEventListener('pointerdown', tryPlay, { once: true });
    const unsub = subscribe(() => { audio.volume = effectiveMusicVolume(); });

    return () => {
      unsub();
      document.removeEventListener('pointerdown', tryPlay);
      audio.pause();
      audio.currentTime = 0;
    };
  }, []);

  const pick = (id) => { AudioManager.play('CLICK'); setSelectedClass(id); };

  const start = () => {
    AudioManager.play('CLICK');
    if (audioRef.current) { audioRef.current.pause(); audioRef.current.currentTime = 0; }
    new Audio(descendSound).play().catch(() => {});
    onSelect(selectedClass, difficulty, playerName.trim(), strongerBosses);
  };

  return (
    <div className={`hero-select ${landscape ? 'landscape' : 'portrait'}`}>
      {/* splash-art banner background; keyed so the brighten-in animation replays on change */}
      <img key={hero.id} className="hero-splash" src={hero.splash} alt="" />
      <div className="hero-vignette-left" />
      <div className="hero-vignette-right" />

      <div className="hero-ui">
        <h1 className="hero-title">Choose Your Hero</h1>

        <div className="hero-busts">
          {HEROES.map(h => (
            <button
              key={h.id}
              className={`hero-bust-btn ${selectedClass === h.id ? 'selected' : ''}`}
              onClick={() => pick(h.id)}
              aria-label={h.name}
            >
              <HeroBust sheet={h.sheet} selected={selectedClass === h.id} />
            </button>
          ))}
        </div>

        <h2 className="hero-name">{hero.name}</h2>
        <p className="hero-desc">{hero.desc}</p>

        <div className="hero-options">
          <div className="hero-difficulty">
            <span className="hero-opt-label">Difficulty</span>
            <div className="hero-diff-btns">
              {['easy', 'normal', 'hard'].map(d => (
                <button
                  key={d}
                  className={`hero-diff-btn ${difficulty === d ? 'active' : ''}`}
                  onClick={() => { AudioManager.play('CLICK'); setDifficulty(d); }}
                >
                  {d.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
          <label className="hero-challenge-toggle">
            <input
              type="checkbox"
              checked={strongerBosses}
              onChange={(e) => { AudioManager.play('CLICK'); setStrongerBosses(e.target.checked); }}
            />
            Stronger Bosses
          </label>
          <input
            className="hero-name-input"
            type="text"
            placeholder="Name (optional)"
            maxLength={20}
            value={playerName}
            onChange={e => setPlayerName(e.target.value)}
          />
        </div>

        <button className="hero-start-btn" onClick={start}>
          <Icon name="ENTER" scale={2} />
          <span>Enter Dungeon</span>
        </button>
      </div>
    </div>
  );
};

export default CharacterSelection;
