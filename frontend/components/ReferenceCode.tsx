"use client";

import { useState } from "react";

export default function ReferenceCode({
  reference,
  copyable = false,
  className = "",
}: {
  reference: string;
  copyable?: boolean;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);

  if (!copyable) {
    return <span className={`reference-code ${className}`}>{reference}</span>;
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(reference);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      // Clipboard access can be denied — the reference is still selectable text.
    }
  }

  return (
    <button
      type="button"
      onClick={handleCopy}
      className={`reference-code inline-flex items-center gap-2 underline decoration-rule underline-offset-4 hover:decoration-ink ${className}`}
      aria-label={`Copy reference ${reference}`}
    >
      <span>{reference}</span>
      <span className="eyebrow" style={{ letterSpacing: "0.08em" }} aria-hidden="true">
        {copied ? "Copied" : "Copy"}
      </span>
    </button>
  );
}
