// Title scene for Online Pixel Dungeon — a faithful re-implementation of
// Shattered Pixel Dungeon's TitleScene. An animated <canvas> (parallax
// background + banner with glow + two torches) sits behind a DOM overlay with
// the 8 menu buttons, version text and a fade-UI toggle. Sub-screens open as
// overlay panels on top.

import { useEffect, useRef, useState } from 'react';
import './menu.css';
import AudioManager from '../audio/AudioManager';
import useTitleAnimation from './useTitleAnimation';
import { effectiveMusicVolume, subscribe } from './menuSettings';
import MenuButton from './MenuButton';
import Icon from './Icon';
import { APP_VERSION } from './content/changelog';

import SettingsPanel from './SettingsPanel';
import ChangesPanel from './ChangesPanel';
import GuidePanel from './GuidePanel';
import AboutPanel from './AboutPanel';
import { RankingsPanel, NewsPanel } from './StubPanels';

import themeMusic from '../assets/pixel-dungeon/themes/theme_1.ogg';

const SUPPORT_URL = 'https://shatteredpixel.com/';

export default function MainMenu({ onStart }) {
  const canvasRef = useRef(null);
  const audioRef = useRef(null);
  const [panel, setPanel] = useState(null);
  const [uiHidden, setUiHidden] = useState(false);
  const [landscape, setLandscape] = useState(
    typeof window !== 'undefined' ? window.innerWidth > window.innerHeight : true
  );

  useTitleAnimation(canvasRef);

  // orientation tracking for the faithful button grid
  useEffect(() => {
    const onResize = () => setLandscape(window.innerWidth > window.innerHeight);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  // menu theme music (loops; volume driven by settings)
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

  const open = (p) => () => setPanel(p);

  // SPD button grid: rows differ by orientation
  const buttons = {
    play:     <MenuButton key="play" icon="ENTER" label="Enter" accent onClick={() => { AudioManager.play('CLICK'); onStart(); }} />,
    support:  <MenuButton key="support" icon="GOLD" label="Support" onClick={() => window.open(SUPPORT_URL, '_blank', 'noopener')} />,
    rankings: <MenuButton key="rankings" icon="RANKINGS" label="Rankings" onClick={open('rankings')} />,
    journal:  <MenuButton key="journal" icon="JOURNAL" label="Guide" onClick={open('guide')} />,
    news:     <MenuButton key="news" icon="NEWS" label="News" onClick={open('news')} />,
    settings: <MenuButton key="settings" icon="PREFS" label="Settings" onClick={open('settings')} />,
    changes:  <MenuButton key="changes" icon="CHANGES" label="Changes" onClick={open('changes')} />,
    about:    <MenuButton key="about" icon="SHPX" label="About" onClick={open('about')} />,
  };

  const rows = landscape
    ? [
        [buttons.play, buttons.support],
        [buttons.rankings, buttons.journal, buttons.news],
        [buttons.settings, buttons.changes, buttons.about],
      ]
    : [
        [buttons.play],
        [buttons.support],
        [buttons.rankings, buttons.journal],
        [buttons.news, buttons.changes],
        [buttons.settings, buttons.about],
      ];

  return (
    <div className="opd-mainmenu">
      <canvas ref={canvasRef} className="opd-title-canvas" />

      {/* click-anywhere catcher to restore the UI after fade */}
      {uiHidden && (
        <div className="opd-fade-catcher" onClick={() => setUiHidden(false)} />
      )}

      <div className={`opd-menu-overlay ${uiHidden ? 'hidden' : ''} ${landscape ? 'landscape' : 'portrait'}`}>
        <div className="opd-menu-buttons">
          {rows.map((row, i) => (
            <div className="opd-menu-row" key={i}>{row}</div>
          ))}
        </div>

        <button
          className="opd-fade-btn"
          aria-label="Hide menu"
          onClick={() => setUiHidden(true)}
        >
          <Icon name="CHEVRON" scale={2} style={{ transform: 'rotate(180deg)' }} />
        </button>

        <span className="opd-version">v{APP_VERSION}</span>
      </div>

      {panel === 'settings' && <SettingsPanel onClose={() => setPanel(null)} />}
      {panel === 'changes' && <ChangesPanel onClose={() => setPanel(null)} />}
      {panel === 'guide' && <GuidePanel onClose={() => setPanel(null)} />}
      {panel === 'about' && <AboutPanel onClose={() => setPanel(null)} />}
      {panel === 'rankings' && <RankingsPanel onClose={() => setPanel(null)} />}
      {panel === 'news' && <NewsPanel onClose={() => setPanel(null)} />}
    </div>
  );
}
