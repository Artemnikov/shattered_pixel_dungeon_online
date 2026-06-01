import Panel from './Panel';
import CHANGELOG from './content/changelog';

export default function ChangesPanel({ onClose }) {
  return (
    <Panel title="Changes" icon="CHANGES" onClose={onClose} wide>
      {CHANGELOG.map((entry) => (
        <div key={entry.version} className="opd-changelog-entry">
          <h3 className="opd-section-title">
            {entry.version} <span className="opd-changelog-name">{entry.title}</span>
          </h3>
          <ul>
            {entry.changes.map((c, i) => <li key={i}>{c}</li>)}
          </ul>
        </div>
      ))}
    </Panel>
  );
}
