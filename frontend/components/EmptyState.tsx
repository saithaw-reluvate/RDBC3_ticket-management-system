export default function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-2 py-16 text-center">
      <p className="text-base text-muted">{title}</p>
      {description && <p className="text-sm text-faint">{description}</p>}
      {action}
    </div>
  );
}
