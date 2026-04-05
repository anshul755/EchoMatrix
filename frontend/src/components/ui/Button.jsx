export default function Button({
  children,
  className = '',
  variant = 'primary',
  ...props
}) {
  return (
    <button
      className={`btn btn-${variant}${className ? ` ${className}` : ''}`}
      {...props}
    >
      {children}
    </button>
  );
}
