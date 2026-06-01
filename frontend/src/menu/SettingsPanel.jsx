import { useEffect, useState } from 'react';
import Panel from './Panel';
import { getSettings, setSetting, subscribe } from './menuSettings';

function Slider({ label, value, onChange, disabled }) {
  return (
    <div className="opd-setting-row">
      <label>{label}</label>
      <input
        type="range" min="0" max="1" step="0.05"
        value={value} disabled={disabled}
        onChange={(e) => onChange(parseFloat(e.target.value))}
      />
      <span className="opd-setting-val">{Math.round(value * 100)}%</span>
    </div>
  );
}

function Toggle({ label, checked, onChange }) {
  return (
    <div className="opd-setting-row">
      <label>{label}</label>
      <button
        className={`opd-toggle ${checked ? 'on' : ''}`}
        onClick={() => onChange(!checked)}
      >
        {checked ? 'ON' : 'OFF'}
      </button>
    </div>
  );
}

export default function SettingsPanel({ onClose }) {
  const [s, setS] = useState(getSettings());
  // re-render on store changes
  useEffect(() => subscribe(setS), []);

  const update = (key, val) => { setSetting(key, val); setS(getSettings()); };

  return (
    <Panel title="Settings" icon="PREFS" onClose={onClose}>
      <h3 className="opd-section-title">Audio</h3>
      <Toggle label="Master mute" checked={s.muted} onChange={(v) => update('muted', v)} />
      <Slider label="Music volume" value={s.musicVolume} disabled={s.muted}
        onChange={(v) => update('musicVolume', v)} />
      <Slider label="SFX volume" value={s.sfxVolume} disabled={s.muted}
        onChange={(v) => update('sfxVolume', v)} />

      <h3 className="opd-section-title">Display</h3>
      <Toggle label="Background animations" checked={s.bgMotion}
        onChange={(v) => update('bgMotion', v)} />
    </Panel>
  );
}
