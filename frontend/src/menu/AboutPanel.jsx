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
          <a href="https://github.com/00-Evan/shattered-pixel-dungeon" target="_blank" rel="noreferrer">Source (GPLv3)</a>
        </p>
      </div>
    </Panel>
  );
}
