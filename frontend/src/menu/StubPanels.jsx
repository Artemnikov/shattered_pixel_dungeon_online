import Panel from './Panel';

// Rankings and News have no online backend yet; show faithful empty states.

export function RankingsPanel({ onClose }) {
  return (
    <Panel title="Rankings" icon="RANKINGS" onClose={onClose}>
      <div className="opd-empty">
        <p>No rankings recorded yet.</p>
        <p className="opd-empty-sub">Finished runs will appear here in a future update.</p>
      </div>
    </Panel>
  );
}

export function NewsPanel({ onClose }) {
  return (
    <Panel title="News" icon="NEWS" onClose={onClose}>
      <div className="opd-empty">
        <p>No news right now.</p>
        <p className="opd-empty-sub">Check back later for updates and announcements.</p>
      </div>
    </Panel>
  );
}
