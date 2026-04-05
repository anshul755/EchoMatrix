export default function Badge({ children, variant = 'accent', className = '' }) {
  return <span className={`badge badge-${variant}${className ? ` ${className}` : ''}`}>{children}</span>;
}
