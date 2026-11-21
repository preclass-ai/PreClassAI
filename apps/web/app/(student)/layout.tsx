import type { ReactNode } from "react";
import { AppShell } from "@/components/shell";
import { DataLink } from "@/features/guest";
import { RequireRole } from "@/lib/auth";

const ROLES = ["STUDENT"] as const;

export default function StudentLayout({ children }: { children: ReactNode }) {
  return (
    <RequireRole roles={ROLES}>
      <AppShell>
        {children}
        <p className="muted small student-data-link">
          <DataLink />
        </p>
      </AppShell>
    </RequireRole>
  );
}
