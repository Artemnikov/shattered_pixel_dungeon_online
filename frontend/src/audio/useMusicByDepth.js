import { useEffect } from 'react';
import { effectiveMusicVolume, subscribe } from '../menu/menuSettings';
import sewers1Music from '../assets/pixel-dungeon/themes/sewers_1.ogg';
import sewers2Music from '../assets/pixel-dungeon/themes/sewers_2.ogg';
import sewers3Music from '../assets/pixel-dungeon/themes/sewers_3.ogg';
import sewersBossMusic from '../assets/pixel-dungeon/themes/sewers_boss.ogg';
import prison1Music from '../assets/pixel-dungeon/themes/prison_1.ogg';
import prison2Music from '../assets/pixel-dungeon/themes/prison_2.ogg';
import prison3Music from '../assets/pixel-dungeon/themes/prison_3.ogg';
import prisonBossMusic from '../assets/pixel-dungeon/themes/prison_boss.ogg';

// SPD's Goo.notice() locks the boss room and starts SEWERS_BOSS looping the
// moment Goo wakes (Level.seal() -> Music.INSTANCE.play(SEWERS_BOSS, true));
// before that playLevelMusic() plays nothing even though Goo is alive. The
// backend mirrors this with a one-shot GOO_FIGHT_STARTED event (see
// App.jsx's onGooFightStarted -> bossFightActive), so the boss track only
// kicks in once the fight actually begins, and stops once Goo dies.
export default function useMusicByDepth({ enabled, depth, bossFightActive, musicRef }) {
  useEffect(() => {
    if (!enabled) return;
    const onBossFloor = depth === 5 && bossFightActive;
    const track = onBossFloor ? sewersBossMusic
      : depth === 1 ? sewers1Music
      : depth === 2 ? sewers2Music
      : depth === 3 ? sewers3Music
      : depth === 4 ? sewers3Music
      : depth === 6 ? prison1Music
      : depth === 7 ? prison2Music
      : depth === 8 ? prison3Music
      : depth === 9 ? prison3Music
      : depth === 10 ? prisonBossMusic
      : null;
    const FADE = 200;
    const steps = 20;
    const interval = FADE / steps;

    // `track` is null on floor 5 outside the boss fight (and once Goo dies,
    // since `bossFightActive` flips back off) — that's "silence": fade out
    // whatever's playing without starting anything new.
    const incoming = track ? new Audio(track) : null;
    if (incoming) incoming.loop = onBossFloor;

    const outgoing = musicRef.current;
    musicRef.current = incoming;
    if (!incoming && !outgoing) return;

    // Crossfade progress (0..1) and the user's volume setting are independent
    // multipliers, combined here so slider/mute changes apply live even
    // mid-fade or mid-track (matches MainMenu's menu-music volume handling).
    let incomingFade = 0;
    let outgoingFade = outgoing ? 1 : 0;
    const applyVolumes = () => {
      const vol = effectiveMusicVolume();
      if (incoming) incoming.volume = incomingFade * vol;
      if (outgoing) outgoing.volume = outgoingFade * vol;
    };

    applyVolumes();
    if (incoming) incoming.play().catch(() => {});

    let step = 0;
    const timer = setInterval(() => {
      step++;
      const t = step / steps;
      outgoingFade = Math.max(0, 1 - t);
      incomingFade = Math.min(1, t);
      applyVolumes();
      if (step >= steps) {
        clearInterval(timer);
        if (outgoing) { outgoing.pause(); outgoing.currentTime = 0; }
      }
    }, interval);

    const unsub = subscribe(applyVolumes);

    return () => {
      unsub();
      clearInterval(timer);
      // If this effect is torn down mid-fade (e.g. depth/bossFightActive flips
      // again before the 200ms crossfade finishes), the orphaned `outgoing`
      // track would otherwise keep playing forever at its last volume.
      if (outgoing) { outgoing.pause(); outgoing.currentTime = 0; }
    };
  }, [enabled, depth, bossFightActive, musicRef]);
}
