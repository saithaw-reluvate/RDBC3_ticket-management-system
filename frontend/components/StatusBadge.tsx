import type { Status } from "@/lib/types";

const STATUS_COPY: Record<Status, string> = {
  OPEN: "Open",
  IN_PROGRESS: "In progress",
  RESOLVED: "Resolved",
};

const STATUS_COLOR: Record<Status, string> = {
  OPEN: "var(--oxide)",
  IN_PROGRESS: "var(--ochre)",
  RESOLVED: "var(--moss)",
};

export default function StatusBadge({ status, pulse = false }: { status: Status; pulse?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm">
      <span
        aria-hidden="true"
        className={`inline-block h-2 w-2 rounded-full ${
          status === "IN_PROGRESS" && pulse ? "status-pulse" : ""
        }`}
        style={{ background: STATUS_COLOR[status] }}
      />
      <span>{STATUS_COPY[status]}</span>
    </span>
  );
}
