import Link from "next/link";
import { attachmentDownloadUrl, ERROR_PRESENTATION, getTicketByToken } from "@/lib/api";
import type { TicketCustomerDetail } from "@/lib/types";
import StatusBadge from "@/components/StatusBadge";
import PriorityMark from "@/components/PriorityMark";
import CategoryTag from "@/components/CategoryTag";
import ReferenceCode from "@/components/ReferenceCode";
import TimelineEntry, { type TimelineEntryProps } from "@/components/TimelineEntry";
import EmptyState from "@/components/EmptyState";
import { formatDateTime, formatFileSize } from "@/lib/format";

function buildTimeline(ticket: TicketCustomerDetail): TimelineEntryProps[] {
  const events: TimelineEntryProps[] = ticket.events.map((event) => ({
    variant: "event",
    eventType: event.event_type,
    oldValue: event.old_value,
    newValue: event.new_value,
    timestamp: event.created_at,
  }));
  const responses: TimelineEntryProps[] = ticket.responses.map((response) => ({
    variant: "response",
    message: response.message,
    timestamp: response.created_at,
  }));
  return [...events, ...responses].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );
}

export default async function TrackPage({ params }: { params: { token: string } }) {
  const backendOrigin = process.env.BACKEND_ORIGIN || "http://localhost:8000";
  const result = await getTicketByToken(params.token, backendOrigin);

  if (!result.ok) {
    const presentation = ERROR_PRESENTATION[result.code];
    return (
      <div className="mx-auto max-w-[580px] px-4 py-16 text-center xs:px-6">
        <p className="eyebrow mb-3">Tracking link</p>
        <h1 className="mb-6 text-2xl font-semibold">{presentation.message}</h1>
        {presentation.action === "request-new-link" && (
          <Link href="/track/link" className="eyebrow underline decoration-rule underline-offset-4">
            Request a new tracking link
          </Link>
        )}
      </div>
    );
  }

  const ticket = result.data;
  const timeline = buildTimeline(ticket);

  return (
    <div className="mx-auto max-w-[700px] px-4 py-12 xs:px-6">
      <div className="mb-8 flex items-center justify-between">
        <StatusBadge status={ticket.status} pulse />
        <span className="text-xs text-faint">Filed {formatDateTime(ticket.created_at)}</span>
      </div>

      <p className="eyebrow mb-2">Ticket record</p>
      <h1 className="mb-8 text-[clamp(31px,5.8vw,43px)] font-semibold leading-tight tracking-[-0.025em]">
        {ticket.subject}
      </h1>

      <dl className="rule grid grid-cols-2 gap-x-6 gap-y-4 py-6 xs:grid-cols-4">
        <div>
          <dt className="eyebrow mb-1">Reference</dt>
          <dd>
            <ReferenceCode reference={ticket.reference} />
          </dd>
        </div>
        <div>
          <dt className="eyebrow mb-1">Priority</dt>
          <dd>
            <PriorityMark priority={ticket.priority} />
          </dd>
        </div>
        <div>
          <dt className="eyebrow mb-1">Category</dt>
          <dd>
            <CategoryTag category={ticket.category} />
          </dd>
        </div>
        <div>
          <dt className="eyebrow mb-1">Filed by</dt>
          <dd className="text-sm">{ticket.reporter_name}</dd>
        </div>
      </dl>

      <section className="rule py-6">
        <h2 className="eyebrow mb-3">Report as filed</h2>
        <p className="whitespace-pre-wrap text-base leading-relaxed">{ticket.description}</p>
      </section>

      {ticket.attachments.length > 0 && (
        <section className="rule py-6">
          <h2 className="eyebrow mb-3">Attachments</h2>
          <ul className="flex flex-col gap-2">
            {ticket.attachments.map((attachment) => (
              <li key={attachment.id}>
                <a
                  href={attachmentDownloadUrl(params.token, attachment.id)}
                  className="text-sm underline decoration-rule underline-offset-4"
                >
                  {attachment.original_filename}{" "}
                  <span className="text-faint">({formatFileSize(attachment.size_bytes)})</span>
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="rule py-6">
        <h2 className="eyebrow mb-3">Activity</h2>
        {timeline.length === 0 ? (
          <EmptyState title="No activity yet beyond filing." />
        ) : (
          <ul>
            {timeline.map((entry, index) => (
              <TimelineEntry key={index} {...entry} />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
