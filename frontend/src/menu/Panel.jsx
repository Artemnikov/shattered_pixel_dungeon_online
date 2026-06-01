// Overlay panel shown on top of the animated title (the parallax keeps running
// behind it). Mirrors how SPD opens windows/scenes from the title menu.
import AudioManager from './../audio/AudioManager';
import Icon from './Icon';

export default function Panel({ title, icon, onClose, children, wide = false }) {
  return (
    <div className="opd-panel-overlay" onClick={onClose}>
      <div
        className={`opd-panel ${wide ? 'wide' : ''}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="opd-panel-header">
          {icon && <Icon name={icon} scale={2} />}
          <h2>{title}</h2>
          <button
            className="opd-panel-close"
            aria-label="Close"
            onClick={() => { AudioManager.play('CLICK'); onClose(); }}
          >
            <Icon name="CLOSE" scale={2} />
          </button>
        </div>
        <div className="opd-panel-body">{children}</div>
      </div>
    </div>
  );
}
