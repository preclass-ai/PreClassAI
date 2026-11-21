"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";
import { ErrorBox } from "@/components/ui";
import { useAuth, type Role } from "@/lib/auth";

const NAV: { href: string; label: string; roles: Role[] }[] = [
  { href: "/lessons", label: "Bài học", roles: ["TEACHER", "REVIEWER"] },
  { href: "/sources", label: "Nguồn", roles: ["TEACHER"] },
  { href: "/plans", label: "Giáo án", roles: ["TEACHER"] },
  { href: "/classes", label: "Lớp & bài giao", roles: ["TEACHER"] },
  { href: "/admin/audit", label: "Nhật ký", roles: ["ADMIN"] },
  { href: "/student", label: "Bài của em", roles: ["STUDENT"] },
];

export function AppShell({ children, narrow }: { children: ReactNode; narrow?: boolean }) {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const [logoutError, setLogoutError] = useState<unknown>(null);
  const [loggingOut, setLoggingOut] = useState(false);
  const links = NAV.filter((n) => user && n.roles.includes(user.role));

  async function handleLogout() {
    setLoggingOut(true);
    setLogoutError(null);
    try {
      await logout();
    } catch (error) {
      setLogoutError(error);
    } finally {
      setLoggingOut(false);
    }
  }

  return (
    <div className="shell">
      <a className="skip-link" href="#main-content">Bỏ qua điều hướng</a>
      <header className="topbar">
        <Link href="/" className="brand" aria-label="PreClass AI">
          <svg className="brand-globe" viewBox="0 0 48 48" fill="none" aria-hidden="true">
            <circle cx="24" cy="24" r="18" stroke="currentColor" strokeWidth="2" />
            <path d="M6 24h36M24 6c6 5 9 11 9 18s-3 13-9 18M24 6c-6 5-9 11-9 18s3 13 9 18" stroke="currentColor" strokeWidth="2" />
            <circle cx="32" cy="15" r="4" fill="currentColor" />
          </svg>
          <span className="brand-copy"><strong>PreClass <em>AI</em></strong><small>Học trước, hiểu sâu</small></span>
        </Link>
        <nav aria-label="Điều hướng chính">
          {links.map((l) => (
            <Link key={l.href} href={l.href} aria-current={pathname.startsWith(l.href) ? "page" : undefined}>
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="topbar-user">
          <span className="muted">{user?.displayName}</span>
          <button type="button" className="link-btn" disabled={loggingOut} onClick={() => void handleLogout()}>
            Đăng xuất
          </button>
        </div>
      </header>
      <ErrorBox error={logoutError} />
      <main id="main-content" tabIndex={-1} className={narrow ? "content content-narrow" : "content"}>{children}</main>
    </div>
  );
}
