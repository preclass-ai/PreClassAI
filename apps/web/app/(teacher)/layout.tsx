import type { ReactNode } from "react";
import { AppShell } from "@/components/shell";
import { DataNotice } from "@/components/ui";
import { GettingStarted } from "@/features/getting-started";
import { RequireRole } from "@/lib/auth";

const ROLES = ["TEACHER", "REVIEWER"] as const;

export default function TeacherLayout({ children }: { children: ReactNode }) {
  return (
    <RequireRole roles={ROLES}>
      <AppShell>
        <GettingStarted role="teacher" />
        {children}
        <DataNotice />
      </AppShell>
    </RequireRole>
  );
}
