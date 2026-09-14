import Link from "next/link";
import ReferenceCode from "@/components/ReferenceCode";

export default function SubmittedPage({
  params,
  searchParams,
}: {
  params: { reference: string };
  searchParams: { email?: string };
}) {
  return (
    <div className="mx-auto max-w-[580px] px-4 py-16 text-center xs:px-6">
      <p className="eyebrow mb-3">Report filed</p>
      <h1 className="mb-6 text-[clamp(36px,7vw,52px)] font-semibold tracking-[-0.025em]">Filed.</h1>

      <div className="mb-8">
        <ReferenceCode reference={params.reference} copyable className="text-lg" />
      </div>

      {searchParams.email && (
        <p className="mb-8 text-sm text-muted">
          We&apos;ll email updates to <span className="text-ink">{searchParams.email}</span>.
        </p>
      )}

      <ul className="rule mb-8 flex flex-col gap-3 pt-6 text-left text-sm text-muted">
        <li>1. We&apos;ll email you a secure link to track this report — no account needed.</li>
        <li>2. Use that link any time to see its status and any replies.</li>
        <li>3. We&apos;ll email you again whenever the status changes or we reply.</li>
      </ul>

      <p className="mb-2 text-sm text-faint">
        Didn&apos;t get the email, or lost the link?
      </p>
      <Link href="/track/link" className="eyebrow underline decoration-rule underline-offset-4">
        Request a new tracking link
      </Link>
    </div>
  );
}
