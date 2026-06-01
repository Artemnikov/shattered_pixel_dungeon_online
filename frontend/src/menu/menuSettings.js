// Lightweight persisted settings store for the menu (audio + display).
// Shared by the Settings panel, AudioManager (SFX volume / mute), the menu
// music player (music volume / mute), and the title animation (bgMotion).

const KEY = 'opd-settings';

const DEFAULTS = {
  musicVolume: 0.7,
  sfxVolume: 0.8,
  muted: false,
  bgMotion: true,
};

function load() {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return { ...DEFAULTS, ...JSON.parse(raw) };
  } catch { /* ignore */ }
  return { ...DEFAULTS };
}

let state = load();
const listeners = new Set();

function persist() {
  try { localStorage.setItem(KEY, JSON.stringify(state)); } catch { /* ignore */ }
}

export function getSettings() {
  return state;
}

export function getDisplaySettings() {
  return state; // bgMotion lives here
}

export function setSetting(key, value) {
  state = { ...state, [key]: value };
  persist();
  listeners.forEach(fn => fn(state));
}

// Effective volumes after mute
export function effectiveSfxVolume() {
  return state.muted ? 0 : state.sfxVolume;
}
export function effectiveMusicVolume() {
  return state.muted ? 0 : state.musicVolume;
}

export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

// alias used by the animation hook
export const subscribeDisplay = subscribe;
