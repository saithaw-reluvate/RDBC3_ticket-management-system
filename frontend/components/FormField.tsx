export default function FormField({
  id,
  label,
  error,
  helperText,
  required = false,
  children,
}: {
  id: string;
  label: string;
  error?: string;
  helperText?: string;
  required?: boolean;
  children: (args: { describedBy: string | undefined; invalid: boolean }) => React.ReactNode;
}) {
  const errorId = `${id}-error`;
  const helperId = `${id}-helper`;
  const describedBy = error ? errorId : helperText ? helperId : undefined;

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="eyebrow">
        {label}
        {required && <span aria-hidden="true"> *</span>}
      </label>
      {children({ describedBy, invalid: Boolean(error) })}
      {helperText && !error && (
        <p id={helperId} className="text-xs text-faint">
          {helperText}
        </p>
      )}
      {error && (
        <p id={errorId} className="text-xs text-oxide" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
