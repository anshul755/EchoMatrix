import { Card } from './Card';

export function LoadingState({ label }) {
  return (
    <div className="loading-spinner">
      <div className="spinner" />
      <span>{label}</span>
    </div>
  );
}

export function EmptyState({ icon, title, description }) {
  return (
    <div className="empty-state">
      {icon}
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}

export function ErrorState({ icon, message }) {
  return (
    <Card className="state-error">
      <div className="state-error-row">
        {icon}
        <span>{message}</span>
      </div>
    </Card>
  );
}
