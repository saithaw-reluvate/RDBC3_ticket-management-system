"use client";

import { useEffect } from "react";

export type ToastVariant = "success" | "error" | "info";

const VARIANT_COLOR: Record<ToastVariant, string> = {
  success: "var(--moss)",
  error: "var(--oxide)",
  info: "var(--ink)",
};

export default function Toast({
  message,
  variant = "info",
  onDismiss,
  duration = 4000,
}: {
  message: string;
  variant?: ToastVariant;
  onDismiss?: () => void;
  /** ms before auto-dismiss; pass 0 to disable (stays until manually dismissed). */
  duration?: number;
}) {
  useEffect(() => {
    if (!onDismiss || duration <= 0) return;
    const timer = setTimeout(onDismiss, duration);
    return () => clearTimeout(timer);
  }, [onDismiss, duration, message]);

  return (
    <div
      role="status"
      className="fixed bottom-4 right-4 z-50 max-w-sm border bg-surface px-4 py-3"
      style={{ borderColor: VARIANT_COLOR[variant] }}
    >
      <p className="text-sm">{message}</p>
      {onDismiss && (
        <button type="button" onClick={onDismiss} className="eyebrow mt-1" aria-label="Dismiss notification">
          Dismiss
        </button>
      )}
    </div>
  );
}
