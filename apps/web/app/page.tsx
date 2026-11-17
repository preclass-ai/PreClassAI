"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { homeFor, useAuth } from "@/lib/auth";

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!loading) router.replace(user ? homeFor(user.role) : "/login");
  }, [user, loading, router]);
  return <div className="page-loading" aria-busy="true">Đang tải…</div>;
}
