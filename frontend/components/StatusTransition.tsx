const LABELS: Record<string, string> = {
  OPEN: "Open",
  IN_PROGRESS: "In progress",
  RESOLVED: "Resolved",
  LOW: "Low",
  MEDIUM: "Medium",
  HIGH: "High",
};

function label(value: string): string {
  return LABELS[value] ?? value;
}

export default function StatusTransition({ oldValue, newValue }: { oldValue: string; newValue: string }) {
  return (
    <span className="text-sm">
      <span className="text-faint line-through">{label(oldValue)}</span>
      <span aria-hidden="true"> {"→"} </span>
      <span>{label(newValue)}</span>
    </span>
  );
}
