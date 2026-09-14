import type { Priority } from "@/lib/types";

const PRIORITY_MARK: Record<Priority, string> = {
  HIGH: "▲",
  MEDIUM: "■",
  LOW: "–",
};

const PRIORITY_COPY: Record<Priority, string> = {
  HIGH: "High",
  MEDIUM: "Medium",
  LOW: "Low",
};

const PRIORITY_COLOR: Record<Priority, string> = {
  HIGH: "var(--oxide)",
  MEDIUM: "var(--ink)",
  LOW: "var(--faint)",
};

export default function PriorityMark({ priority }: { priority: Priority }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-sm">
      <span aria-hidden="true" style={{ color: PRIORITY_COLOR[priority] }}>
        {PRIORITY_MARK[priority]}
      </span>
      <span>{PRIORITY_COPY[priority]}</span>
    </span>
  );
}
