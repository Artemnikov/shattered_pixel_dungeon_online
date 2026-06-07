import { useEffect } from 'react';
import sewers1Music from '../assets/pixel-dungeon/themes/sewers_1.ogg';
import sewers2Music from '../assets/pixel-dungeon/themes/sewers_2.ogg';
import sewers3Music from '../assets/pixel-dungeon/themes/sewers_3.ogg';
import prison1Music from '../assets/pixel-dungeon/themes/prison_1.ogg';
import prison2Music from '../assets/pixel-dungeon/themes/prison_2.ogg';
import prison3Music from '../assets/pixel-dungeon/themes/prison_3.ogg';
import prisonBossMusic from '../assets/pixel-dungeon/themes/prison_boss.ogg';

export default function useMusicByDepth({ enabled, depth, musicRef }) {
  useEffect(() => {
    if (!enabled) return;
    const track = depth === 1 ? sewers1Music : depth === 2 ? sewers2Music : depth === 3 ? sewers3Music : depth === 4 ? sewers3Music : depth === 6 ? prison1Music : depth === 7 ? prison2Music : depth === 8 ? prison3Music : depth === 9 ? prison3Music : depth === 10 ? prisonBossMusic : null;
    if (!track) return;

    const FADE = 200;
    const steps = 20;
    const interval = FADE / steps;

    const incoming = new Audio(track);
    incoming.loop = false;
    incoming.volume = 0;
    incoming.play().catch(() => {});

    const outgoing = musicRef.current;
    musicRef.current = incoming;

    let step = 0;
    const timer = setInterval(() => {
      step++;
      const t = step / steps;
      if (outgoing) outgoing.volume = Math.max(0, 1 - t);
      incoming.volume = Math.min(1, t);
      if (step >= steps) {
        clearInterval(timer);
        if (outgoing) { outgoing.pause(); outgoing.currentTime = 0; }
      }
    }, interval);

    return () => { clearInterval(timer); };
  }, [enabled, depth, musicRef]);
}
