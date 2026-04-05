export function Card({ children, className = '', ...props }) {
  return (
    <section className={`card${className ? ` ${className}` : ''}`} {...props}>
      {children}
    </section>
  );
}

export function CardHeader({ title, subtitle, action, children }) {
  return (
    <div className="card-header">
      <div>
        {title ? <div className="card-title">{title}</div> : null}
        {subtitle ? <div className="card-subtitle">{subtitle}</div> : null}
        {children}
      </div>
      {action}
    </div>
  );
}
