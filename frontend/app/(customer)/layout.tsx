import Link from "next/link";
import ThemeToggle from "@/components/ThemeToggle";

// The customer side gets only a wordmark and a "Track a ticket" link — a nav
// bar in front of someone in distress is noise (docs/FRONTEND.md §3).
export default function CustomerLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-page">
      <header className="rule flex items-center justify-between px-4 py-4 xs:px-6">
        <Link href="/" className="text-sm font-semibold tracking-[0.02em]">
          Dispatch
        </Link>
        <nav className="flex items-center gap-4">
          <Link href="/track/link" className="eyebrow underline decoration-rule underline-offset-4">
            Track a ticket
          </Link>
          <ThemeToggle />
        </nav>
      </header>
      <main>{children}</main>
    </div>
  );
}
