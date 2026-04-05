import { Card } from './Card';

export default function StatCard({ icon, label, value, detail }) {
  return (
    <Card className="stat-card">
      <div className="stat-label">
        <span className="stat-icon">{icon}</span>
        {label}
      </div>
      <div className="stat-value">{value}</div>
      {detail ? <div className="stat-detail">{detail}</div> : null}
    </Card>
  );
}
