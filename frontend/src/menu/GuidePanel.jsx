import Panel from './Panel';
import GUIDE from './content/guide';

export default function GuidePanel({ onClose }) {
  return (
    <Panel title="Guide" icon="JOURNAL" onClose={onClose} wide>
      {GUIDE.map((section) => (
        <div key={section.title} className="opd-guide-section">
          <h3 className="opd-section-title">{section.title}</h3>
          {section.body.map((p, i) => <p key={i}>{p}</p>)}
        </div>
      ))}
    </Panel>
  );
}
