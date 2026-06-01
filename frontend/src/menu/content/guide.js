// Brief, remake-specific gameplay guide shown in the Guide panel.
const GUIDE = [
  {
    title: 'Getting Started',
    body: [
      'Pick a class from the hero select screen, optionally set a difficulty and name, then enter the dungeon.',
      'Click a tile to walk there. Click an adjacent enemy to attack it.',
      'Your goal is to descend as deep as you can — find the stairs down on each floor.',
    ],
  },
  {
    title: 'Combat & Items',
    body: [
      'Equip weapons and armor from your inventory; ranged weapons enter a targeting mode — click a tile to fire.',
      'Drink potions and use items from the toolbar at the bottom of the screen.',
      'Watch your health: it regenerates slowly over time, and a low-health warning will sound.',
    ],
  },
  {
    title: 'Classes',
    body: [
      'Warrior — sturdy melee fighter, starts with a shortsword and cloth armor.',
      'Mage — wields a magic staff with limited charges.',
      'Rogue — agile, starts with a dagger and cloak.',
      'Archer — ranged specialist with a spirit bow.',
    ],
  },
  {
    title: 'Multiplayer',
    body: [
      'The dungeon is shared in real time over WebSocket — other players appear on your floor.',
      'If you fall, you can start a new run or return to the main menu from the game-over screen.',
    ],
  },
];

export default GUIDE;
