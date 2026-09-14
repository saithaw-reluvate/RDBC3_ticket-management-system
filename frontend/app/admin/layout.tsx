import AdminAuthProvider from "@/components/AdminAuthProvider";
import AdminTopBar from "@/components/AdminTopBar";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <AdminAuthProvider>
      <AdminTopBar />
      {children}
    </AdminAuthProvider>
  );
}
