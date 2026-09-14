"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import FormField from "@/components/FormField";
import CategorySelect from "@/components/CategorySelect";
import DropZone from "@/components/DropZone";
import { createTicket, ERROR_PRESENTATION } from "@/lib/api";
import type { Category } from "@/lib/types";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

interface FieldErrors {
  reporter_name?: string;
  email?: string;
  subject?: string;
  category?: string;
  description?: string;
  attachments?: string;
}

export default function ReportPage() {
  const router = useRouter();
  const [reporterName, setReporterName] = useState("");
  const [email, setEmail] = useState("");
  const [subject, setSubject] = useState("");
  const [category, setCategory] = useState<Category | "">("");
  const [description, setDescription] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [sealed, setSealed] = useState(false);

  function validate(): FieldErrors {
    const next: FieldErrors = {};
    if (!reporterName.trim()) next.reporter_name = "Enter your name.";
    if (!email.trim()) next.email = "Enter your email.";
    else if (!EMAIL_RE.test(email.trim())) next.email = "Enter a valid email address.";
    if (!subject.trim()) next.subject = "Enter a subject.";
    if (!category) next.category = "Select a category.";
    if (!description.trim()) next.description = "Describe what happened.";
    return next;
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setFormError(null);
    const fieldErrors = validate();
    setErrors(fieldErrors);
    if (Object.keys(fieldErrors).length > 0) return;

    setSubmitting(true);
    const formData = new FormData();
    formData.set("reporter_name", reporterName.trim());
    formData.set("email", email.trim());
    formData.set("subject", subject.trim());
    formData.set("category", category);
    formData.set("description", description.trim());
    files.forEach((file) => formData.append("attachments", file));

    const result = await createTicket(formData);
    setSubmitting(false);

    if (!result.ok) {
      if (result.code === "validation_error") {
        const details = result.details as Record<string, string[] | string>;
        const mapped: FieldErrors = {};
        for (const [field, messages] of Object.entries(details)) {
          const message = Array.isArray(messages) ? messages[0] : messages;
          if (field in fieldErrors || ["reporter_name", "email", "subject", "category", "description", "attachments"].includes(field)) {
            (mapped as Record<string, string>)[field] = String(message);
          }
        }
        setErrors(mapped);
        setFormError(Object.keys(mapped).length ? null : ERROR_PRESENTATION.validation_error.message);
      } else {
        setFormError(ERROR_PRESENTATION[result.code].message);
      }
      return;
    }

    setSealed(true);
    setTimeout(() => {
      router.push(`/submitted/${result.data.reference}?email=${encodeURIComponent(email.trim())}`);
    }, 320);
  }

  return (
    <div className="mx-auto max-w-[700px] px-4 py-12 xs:px-6">
      <p className="eyebrow mb-3">Incident report</p>
      <h1 className="mb-8 text-[clamp(36px,7vw,52px)] font-semibold leading-tight tracking-[-0.025em]">
        Report an incident
      </h1>

      <form onSubmit={handleSubmit} className={`flex flex-col gap-6 ${sealed ? "seal-animate" : ""}`} noValidate>
        <FormField id="reporter_name" label="Your name" required error={errors.reporter_name}>
          {({ describedBy, invalid }) => (
            <input
              id="reporter_name"
              type="text"
              value={reporterName}
              onChange={(e) => setReporterName(e.target.value)}
              aria-describedby={describedBy}
              aria-invalid={invalid}
              className="w-full border-0 border-b border-rule bg-transparent py-2 text-base focus:border-oxide focus:outline-none"
            />
          )}
        </FormField>

        <FormField id="email" label="Email address" required error={errors.email}>
          {({ describedBy, invalid }) => (
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              aria-describedby={describedBy}
              aria-invalid={invalid}
              className="w-full border-0 border-b border-rule bg-transparent py-2 text-base focus:border-oxide focus:outline-none"
            />
          )}
        </FormField>

        <FormField id="subject" label="Subject" required error={errors.subject}>
          {({ describedBy, invalid }) => (
            <input
              id="subject"
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              aria-describedby={describedBy}
              aria-invalid={invalid}
              className="w-full border-0 border-b border-rule bg-transparent py-2 text-base focus:border-oxide focus:outline-none"
            />
          )}
        </FormField>

        <FormField id="category" label="Category" required error={errors.category}>
          {({ describedBy, invalid }) => (
            <CategorySelect
              id="category"
              value={category}
              onChange={setCategory}
              required
              ariaDescribedBy={describedBy}
              ariaInvalid={invalid}
            />
          )}
        </FormField>

        <FormField id="description" label="Description" required error={errors.description}>
          {({ describedBy, invalid }) => (
            <textarea
              id="description"
              rows={6}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              aria-describedby={describedBy}
              aria-invalid={invalid}
              className="w-full resize-y border-0 border-b border-rule bg-transparent py-2 text-base focus:border-oxide focus:outline-none"
            />
          )}
        </FormField>

        <FormField id="attachments" label="Attachments (optional)" error={errors.attachments}>
          {({ describedBy }) => (
            <DropZone id="attachments" files={files} onChange={setFiles} ariaDescribedBy={describedBy} />
          )}
        </FormField>

        {formError && (
          <p role="alert" className="text-sm text-oxide">
            {formError}
          </p>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="eyebrow self-start bg-ink px-6 py-3 text-[color:var(--surface)] disabled:opacity-50"
        >
          {submitting ? "Filing…" : "File report"}
        </button>
      </form>
    </div>
  );
}
