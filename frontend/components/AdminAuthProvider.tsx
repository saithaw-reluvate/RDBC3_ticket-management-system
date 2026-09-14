"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { adminLogout, adminMe } from "@/lib/api";
import type { AdminUser } from "@/lib/types";

interface AdminAuthContextValue {
  user: AdminUser | null;
  checked: boolean;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

const AdminAuthContext = createContext<AdminAuthContextValue>({
  user: null,
  checked: false,
  refresh: async () => {},
  logout: async () => {},
});

export function useAdminAuth(): AdminAuthContextValue {
  return useContext(AdminAuthContext);
}

export default function AdminAuthProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<AdminUser | null>(null);
  const [checked, setChecked] = useState(false);

  const refresh = useCallback(async () => {
    const result = await adminMe();
    if (result.ok) {
      setUser(result.data);
    } else {
      setUser(null);
      // 403 while signed out is the normal state, not an error to surface —
      // docs/FRONTEND.md §10. Just redirect unless already on the login page.
      if (pathname !== "/admin/login") {
        router.replace("/admin/login");
      }
    }
    setChecked(true);
  }, [pathname, router]);

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  const logout = useCallback(async () => {
    await adminLogout();
    setUser(null);
    router.replace("/admin/login");
  }, [router]);

  const value: AdminAuthContextValue = { user, checked, refresh, logout };

  if (pathname === "/admin/login") {
    return <AdminAuthContext.Provider value={value}>{children}</AdminAuthContext.Provider>;
  }

  if (!checked || !user) {
    // Either still checking, or a redirect to /admin/login is in flight.
    return (
      <AdminAuthContext.Provider value={value}>
        <div className="min-h-screen bg-page" aria-busy={!checked} />
      </AdminAuthContext.Provider>
    );
  }

  return <AdminAuthContext.Provider value={value}>{children}</AdminAuthContext.Provider>;
}
