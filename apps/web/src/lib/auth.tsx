"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, type ReactNode } from "react";
import { api, ApiError, setUnauthenticatedHandler, unwrap, type Schemas } from "./api";
import { useAfter } from "./http";

export type User = Schemas["UserOut"];
export type Role = User["role"];

interface AuthState {
  user: User | null;
  loading: boolean;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export const ME_KEY = ["me"] as const;

export function homeFor(role: Role): string {
  switch (role) {
    case "STUDENT":
      return "/student";
    case "ADMIN":
      return "/admin/audit";
    default:
      return "/lessons";
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const router = useRouter();
  const pathname = usePathname();

  const me = useQuery({
    queryKey: ME_KEY,
    queryFn: async () => {
      try {
        return await unwrap(api.GET("/v1/me"), { quiet401: true });
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) return null;
        throw e;
      }
    },
    staleTime: 5 * 60_000,
  });

  useEffect(() => {
    setUnauthenticatedHandler(() => {
      qc.setQueryData(ME_KEY, null);
      if (!window.location.pathname.startsWith("/login")) {
        router.replace(`/login?next=${encodeURIComponent(window.location.pathname)}`);
      }
    });
    return () => setUnauthenticatedHandler(null);
  }, [qc, router]);

  const logout = useCallback(async () => {
    try {
      await unwrap(api.POST("/v1/auth/logout"), { quiet401: true });
    } catch (error) {
      if (!(error instanceof ApiError && error.status === 401)) throw error;
    }
    qc.clear();
    qc.setQueryData(ME_KEY, null);
    router.replace("/login");
  }, [qc, router]);

  // Keep a stale cache from showing another user's data after a pathname change to /login.
  useEffect(() => {
    if (pathname === "/login") qc.removeQueries({ predicate: (q) => q.queryKey[0] !== ME_KEY[0] });
  }, [pathname, qc]);

  return (
    <AuthContext.Provider value={{ user: me.data ?? null, loading: me.isPending, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

/** Client-side route guard. The server enforces roles regardless; this only avoids showing dead screens. */
export function RequireRole({ roles, children }: { roles: readonly Role[]; children: ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const allowed = !!user && roles.includes(user.role);

  useEffect(() => {
    if (loading) return;
    if (!user) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    else if (!roles.includes(user.role)) router.replace(homeFor(user.role));
  }, [loading, user, roles, router, pathname]);

  const stuck = useAfter(!allowed, 20_000); // never an endless spinner: after 20 s offer a retry
  if (!allowed && stuck) {
    return (
      <div className="page-loading" role="alert">
        <p>Không tải được trang. Máy chủ có thể đang khởi động, thử lại sau ít giây.</p>
        <button type="button" className="btn btn-primary" onClick={() => window.location.reload()}>
          Thử lại
        </button>
      </div>
    );
  }
  if (!allowed) return <div className="page-loading" aria-busy="true">Đang tải…</div>;
  return <>{children}</>;
}
