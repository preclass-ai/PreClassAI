import type { ReactNode } from "react";
import { AppShell } from "@/components/shell";
import { RequireRole } from "@/lib/auth";

const ROLES = ["TEACHER", "REVIEWER"] as const;

export default function TeacherLayout({ children }: { children: ReactNode }) {
  return (
    <RequireRole roles={ROLES}>
      <AppShell>{children}</AppShell>
    </RequireRole>
  );
}
