import type { ReactNode } from "react";
import { AppShell } from "@/components/shell";
import { RequireRole } from "@/lib/auth";

const ROLES = ["ADMIN"] as const;

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <RequireRole roles={ROLES}>
      <AppShell>{children}</AppShell>
    </RequireRole>
  );
}
