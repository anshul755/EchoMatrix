export default function Input({
  icon,
  className = '',
  inputClassName = '',
  ...props
}) {
  return (
    <div className={`control-shell${className ? ` ${className}` : ''}`}>
      {icon}
      <input className={inputClassName} {...props} />
    </div>
  );
}
