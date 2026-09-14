"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAdminAuth } from "./AdminAuthProvider";
import ThemeToggle from "./ThemeToggle";

export default function AdminTopBar() {
  const pathname = usePathname();
  const { user, logout } = useAdminAuth();

  if (pathname === "/admin/login" || !user) return null;

  return (
    <header className="rule flex items-center justify-between px-4 py-3 xs:px-6">
      <Link href="/admin" className="text-sm font-semibold tracking-[0.02em]">
        Dispatch {"—"} Admin
      </Link>
      <div className="flex items-center gap-4">
        <span className="text-sm text-muted">{user.username}</span>
        <button type="button" onClick={logout} className="eyebrow underline decoration-rule underline-offset-4">
          Log out
        </button>
        <ThemeToggle />
      </div>
    </header>
  );
}
