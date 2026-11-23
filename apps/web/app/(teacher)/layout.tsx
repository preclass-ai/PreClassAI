import type { ReactNode } from "react";
import { AppShell } from "@/components/shell";
import { DataNotice } from "@/components/ui";
import { TeacherCompanion } from "@/features/teacher-guide/companion";
import { RequireRole } from "@/lib/auth";

const ROLES = ["TEACHER", "REVIEWER"] as const;

export default function TeacherLayout({ children }: { children: ReactNode }) {
  return (
    <RequireRole roles={ROLES}>
      <AppShell>
        {children}
        <DataNotice />
        <TeacherCompanion />
      </AppShell>
    </RequireRole>
  );
}
