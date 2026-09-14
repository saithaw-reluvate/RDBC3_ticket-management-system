"use client";

import { useRef, useState } from "react";
import { formatFileSize } from "@/lib/format";

const ALLOWED_EXTENSIONS = ["png", "jpg", "jpeg", "gif", "webp", "pdf", "txt", "log", "csv"];
export const MAX_FILES = 5;
export const MAX_BYTES = 5 * 1024 * 1024;

function extensionOf(filename: string): string {
  return filename.includes(".") ? filename.split(".").pop()!.toLowerCase() : "";
}

export function validateFiles(existing: File[], incoming: File[]): { files: File[]; error: string | null } {
  const combined = [...existing, ...incoming];
  if (combined.length > MAX_FILES) {
    return { files: existing, error: `You can attach up to ${MAX_FILES} files.` };
  }
  for (const file of incoming) {
    const ext = extensionOf(file.name);
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      return { files: existing, error: `"${file.name}" is not an allowed file type.` };
    }
    if (file.size > MAX_BYTES) {
      return { files: existing, error: `"${file.name}" is larger than 5 MB.` };
    }
  }
  return { files: combined, error: null };
}

export default function DropZone({
  id,
  files,
  onChange,
  ariaDescribedBy,
}: {
  id: string;
  files: File[];
  onChange: (files: File[]) => void;
  ariaDescribedBy?: string;
}) {
  const [localError, setLocalError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleIncoming(incoming: File[]) {
    const result = validateFiles(files, incoming);
    setLocalError(result.error);
    if (!result.error) onChange(result.files);
  }

  function removeFile(index: number) {
    setLocalError(null);
    onChange(files.filter((_, i) => i !== index));
  }

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          handleIncoming(Array.from(e.dataTransfer.files));
        }}
        className={`flex flex-col items-center gap-2 border border-dashed px-4 py-6 text-center transition-colors ${
          dragActive ? "border-oxide" : "border-rule-strong"
        }`}
      >
        <p className="text-sm text-muted">Drag files here, or</p>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="eyebrow underline decoration-rule underline-offset-4"
        >
          Choose files
        </button>
        <p className="text-xs text-faint">
          Up to {MAX_FILES} files, 5 MB each. PNG, JPG, GIF, WEBP, PDF, TXT, LOG, CSV.
        </p>
        <input
          ref={inputRef}
          id={id}
          type="file"
          multiple
          className="sr-only"
          aria-describedby={ariaDescribedBy}
          onChange={(e) => {
            if (e.target.files) handleIncoming(Array.from(e.target.files));
            e.target.value = "";
          }}
        />
      </div>

      {localError && (
        <p role="alert" className="mt-2 text-xs text-oxide">
          {localError}
        </p>
      )}

      {files.length > 0 && (
        <ul className="mt-3 flex flex-col gap-1">
          {files.map((file, index) => (
            <li key={`${file.name}-${index}`} className="flex items-center justify-between gap-2 text-sm">
              <span className="truncate">
                {file.name} <span className="text-faint">({formatFileSize(file.size)})</span>
              </span>
              <button
                type="button"
                onClick={() => removeFile(index)}
                className="eyebrow shrink-0 text-oxide"
                aria-label={`Remove ${file.name}`}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
