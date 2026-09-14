import StatusTransition from "./StatusTransition";
import { formatDateTime } from "@/lib/format";

const EVENT_LABELS: Record<string, string> = {
  CREATED: "Filed",
  STATUS_CHANGED: "Status changed",
  PRIORITY_CHANGED: "Priority changed",
  CATEGORY_CHANGED: "Category changed",
  RESPONSE_ADDED: "Response added",
  ATTACHMENT_ADDED: "Attachment added",
  TOKEN_ISSUED: "Tracking link issued",
  TOKEN_REVOKED: "Tracking links revoked",
  EMAIL_SENT: "Notification sent",
  EMAIL_FAILED: "Notification failed to send",
};

export type TimelineEntryProps =
  | {
      variant: "event";
      eventType: string;
      oldValue: string | null;
      newValue: string | null;
      timestamp: string;
    }
  | { variant: "response"; message: string; timestamp: string }
  | { variant: "internal-note"; message: string; timestamp: string; author?: string | null }
  | { variant: "attachment"; filename: string; timestamp: string };

export default function TimelineEntry(props: TimelineEntryProps) {
  return (
    <li
      className={`rule py-3 first:border-t-0 ${
        props.variant === "internal-note" ? "bg-internal-bg px-3 -mx-3" : ""
      }`}
    >
      <div className="flex items-baseline justify-between gap-4">
        <div className="min-w-0">{renderBody(props)}</div>
        <time
          dateTime={props.timestamp}
          className="shrink-0 text-xs text-faint tabular-nums"
        >
          {formatDateTime(props.timestamp)}
        </time>
      </div>
    </li>
  );
}

function renderBody(props: TimelineEntryProps) {
  switch (props.variant) {
    case "event": {
      const label = EVENT_LABELS[props.eventType] ?? props.eventType;
      if (props.oldValue && props.newValue) {
        return (
          <span className="text-sm">
            <span className="text-muted">{label}: </span>
            <StatusTransition oldValue={props.oldValue} newValue={props.newValue} />
          </span>
        );
      }
      return <span className="text-sm text-muted">{label}</span>;
    }
    case "response":
      return <p className="text-sm">{props.message}</p>;
    case "internal-note":
      return (
        <div>
          <span className="eyebrow mb-1 inline-block" style={{ color: "var(--ochre)" }}>
            Internal note{props.author ? ` — ${props.author}` : ""}
          </span>
          <p className="text-sm">{props.message}</p>
        </div>
      );
    case "attachment":
      return <span className="text-sm text-muted">Attachment added: {props.filename}</span>;
    default:
      return null;
  }
}
