"use client";

import { useCallback, useEffect, useState } from "react";
import {
  adminAddResponse,
  adminAttachmentDownloadUrl,
  adminGetTicket,
  adminPatchTicket,
  adminResendLink,
  adminRevokeLinks,
} from "@/lib/api";
import { CATEGORIES, PRIORITIES, STATUSES, type Category, type Priority, type Status, type TicketAdminDetail } from "@/lib/types";
import TimelineEntry, { type TimelineEntryProps } from "@/components/TimelineEntry";
import Composer from "@/components/Composer";
import SkeletonRow from "@/components/SkeletonRow";
import EmptyState from "@/components/EmptyState";
import Toast, { type ToastVariant } from "@/components/Toast";
import { formatDateTime, formatFileSize } from "@/lib/format";

function buildTimeline(ticket: TicketAdminDetail): TimelineEntryProps[] {
  const events: TimelineEntryProps[] = ticket.events.map((event) => ({
    variant: "event",
    eventType: event.event_type,
    oldValue: event.old_value,
    newValue: event.new_value,
    timestamp: event.created_at,
  }));
  const responses: TimelineEntryProps[] = ticket.responses.map((response) =>
    response.is_internal
      ? { variant: "internal-note", message: response.message, timestamp: response.created_at, author: response.author }
      : { variant: "response", message: response.message, timestamp: response.created_at }
  );
  return [...events, ...responses].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );
}

export default function TicketWorkspacePage({ params }: { params: { reference: string } }) {
  const [ticket, setTicket] = useState<TicketAdminDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [toast, setToast] = useState<{ message: string; variant: ToastVariant } | null>(null);
  const [confirmingRevoke, setConfirmingRevoke] = useState(false);
  const [composerSubmitting, setComposerSubmitting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const result = await adminGetTicket(params.reference);
    if (result.ok) {
      setTicket(result.data);
      setNotFound(false);
    } else if (result.code === "not_found") {
      setNotFound(true);
    }
    setLoading(false);
  }, [params.reference]);

  useEffect(() => {
    load();
  }, [load]);

  async function handlePatch(patch: Partial<{ status: Status; priority: Priority; category: Category }>) {
    if (!ticket) return;
    const previous = ticket;
    setTicket({ ...ticket, ...patch });
    const result = await adminPatchTicket(params.reference, patch);
    if (result.ok) {
      setTicket(result.data);
    } else {
      setTicket(previous);
      setToast({ message: "That change didn't save. Please try again.", variant: "error" });
    }
  }

  async function handleComposerSubmit(message: string, isInternal: boolean) {
    setComposerSubmitting(true);
    const result = await adminAddResponse(params.reference, message, isInternal);
    setComposerSubmitting(false);
    if (result.ok) {
      await load();
      setToast({ message: isInternal ? "Internal note added." : "Reply sent.", variant: "success" });
    } else {
      setToast({ message: "That reply didn't send. Please try again.", variant: "error" });
    }
  }

  async function handleResendLink() {
    const result = await adminResendLink(params.reference);
    setToast(
      result.ok
        ? { message: "Tracking link resent.", variant: "success" }
        : { message: "Couldn't resend the link. Please try again.", variant: "error" }
    );
  }

  async function handleRevokeLinks() {
    setConfirmingRevoke(false);
    const result = await adminRevokeLinks(params.reference);
    setToast(
      result.ok
        ? { message: `Revoked ${result.data.revoked} tracking link(s).`, variant: "success" }
        : { message: "Couldn't revoke links. Please try again.", variant: "error" }
    );
  }

  if (loading) {
    return (
      <div className="flex flex-col gap-4 p-6">
        {Array.from({ length: 5 }).map((_, index) => (
          <SkeletonRow key={index} />
        ))}
      </div>
    );
  }

  if (notFound || !ticket) {
    return (
      <div className="p-6">
        <EmptyState title="Ticket not found." />
      </div>
    );
  }

  const timeline = buildTimeline(ticket);

  return (
    <div className="flex h-full flex-col overflow-y-auto px-6 py-6">
      <p className="reference-code mb-1 text-sm">{ticket.reference}</p>
      <h1 className="mb-4 text-2xl font-semibold">{ticket.subject}</h1>
      <p className="mb-6 text-sm text-muted">
        {ticket.reporter_name} {"·"} {ticket.client_email} {"·"} filed {formatDateTime(ticket.created_at)}
      </p>

      <div className="rule mb-6 flex flex-wrap items-end gap-6 py-4">
        <div>
          <label htmlFor="status-select" className="eyebrow mb-1 block">
            Status
          </label>
          <select
            id="status-select"
            value={ticket.status}
            onChange={(event) => handlePatch({ status: event.target.value as Status })}
            className="border-0 border-b border-rule bg-transparent py-1 text-sm focus:border-oxide focus:outline-none"
          >
            {STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="priority-select" className="eyebrow mb-1 block">
            Priority
          </label>
          <select
            id="priority-select"
            value={ticket.priority}
            onChange={(event) => handlePatch({ priority: event.target.value as Priority })}
            className="border-0 border-b border-rule bg-transparent py-1 text-sm focus:border-oxide focus:outline-none"
          >
            {PRIORITIES.map((priority) => (
              <option key={priority} value={priority}>
                {priority}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="category-select" className="eyebrow mb-1 block">
            Category
          </label>
          <select
            id="category-select"
            value={ticket.category}
            onChange={(event) => handlePatch({ category: event.target.value as Category })}
            className="border-0 border-b border-rule bg-transparent py-1 text-sm focus:border-oxide focus:outline-none"
          >
            {CATEGORIES.map((category) => (
              <option key={category.value} value={category.value}>
                {category.label}
              </option>
            ))}
          </select>
        </div>
        <div className="ml-auto flex items-center gap-4">
          <button type="button" onClick={handleResendLink} className="eyebrow underline decoration-rule underline-offset-4">
            Resend link
          </button>
          <button
            type="button"
            onClick={() => setConfirmingRevoke(true)}
            className="eyebrow text-oxide underline decoration-rule underline-offset-4"
          >
            Revoke links
          </button>
        </div>
      </div>

      {confirmingRevoke && (
        <div
          role="alertdialog"
          aria-label="Confirm revoke tracking links"
          className="mb-6 flex items-center justify-between gap-4 border border-oxide bg-internal-bg p-4"
        >
          <p className="text-sm">Revoke every active tracking link for this ticket? The customer will need a new one.</p>
          <div className="flex shrink-0 gap-3">
            <button type="button" onClick={() => setConfirmingRevoke(false)} className="eyebrow">
              Cancel
            </button>
            <button type="button" onClick={handleRevokeLinks} className="eyebrow text-oxide">
              Revoke
            </button>
          </div>
        </div>
      )}

      {ticket.attachments.length > 0 && (
        <div className="rule mb-6 py-4">
          <h2 className="eyebrow mb-3">Attachments</h2>
          <ul className="flex flex-col gap-2">
            {ticket.attachments.map((attachment) => (
              <li key={attachment.id}>
                <a
                  href={adminAttachmentDownloadUrl(ticket.reference, attachment.id)}
                  className="text-sm underline decoration-rule underline-offset-4"
                >
                  {attachment.original_filename}{" "}
                  <span className="text-faint">({formatFileSize(attachment.size_bytes)})</span>
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="rule mb-6 py-4">
        <h2 className="eyebrow mb-3">History</h2>
        {timeline.length === 0 ? (
          <EmptyState title="No activity yet beyond filing." />
        ) : (
          <ul>
            {timeline.map((entry, index) => (
              <TimelineEntry key={index} {...entry} />
            ))}
          </ul>
        )}
      </div>

      <Composer reporterName={ticket.reporter_name} onSubmit={handleComposerSubmit} submitting={composerSubmitting} />

      {toast && <Toast message={toast.message} variant={toast.variant} onDismiss={() => setToast(null)} />}
    </div>
  );
}
