// Brief, remake-specific changelog shown in the Changes panel.
export const APP_VERSION = '0.1.0';

const CHANGELOG = [
  {
    version: 'v0.1.0',
    title: 'Online Pixel Dungeon — Title Update',
    changes: [
      'New animated main menu: scrolling parallax background, banner with pulsing glow, and two flickering torches — ported from the original Shattered Pixel Dungeon title screen.',
      'Added Settings (audio + display), Changes, Guide, About, Rankings and News screens.',
      'Audio now has independent music and SFX volume controls plus a master mute.',
      'Display option to toggle background animations.',
    ],
  },
  {
    version: 'v0.0.x',
    title: 'Early Online Prototype',
    changes: [
      'Real-time multiplayer dungeon over WebSocket.',
      'Four playable classes: Warrior, Mage, Rogue, Archer.',
      'Canvas-rendered dungeon with mobs, items, inventory and combat.',
      'Depth-based music and sound effects.',
    ],
  },
];

export default CHANGELOG;
