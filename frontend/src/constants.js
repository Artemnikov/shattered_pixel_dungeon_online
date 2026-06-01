export const TILE_SIZE = 32;
export const TILE_SCALE = 2;
export const MOVE_DURATION = 150;
export const CAMERA_LERP = 0.1;
export const MIN_ZOOM = 0.5;
export const MAX_ZOOM = 2.5;
export const PROJECTILE_SPEED = 0.5;

// Melee attack animation timing (mirrors Shattered Pixel Dungeon)
export const PLAYER_ATTACK_DURATION = 270; // 4 frames @ ~15fps
export const PLAYER_OPERATE_DURATION = 500; // drink/operate: 4 frames @ 8fps (SPD)
export const HIT_CONNECT_DELAY = 130;      // delay before swing "connects" and damage shows
export const FLASH_DURATION = 50;          // white hit-flash duration

export const easeOutQuad = t => 1 - (1 - t) * (1 - t);
