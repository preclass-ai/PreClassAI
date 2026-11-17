"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";
import { errorMessage } from "@/lib/errors";
import type { Tone } from "@/lib/labels";

export function Badge({ tone = "neutral", children, title }: { tone?: Tone; children: ReactNode; title?: string }) {
  return (
    <span className={`badge badge-${tone}`} title={title}>
      {children}
    </span>
  );
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  busy?: boolean;
};

export function Button({ variant = "secondary", busy, disabled, children, className, ...rest }: ButtonProps) {
  return (
    <button
      type="button"
      {...rest}
      className={`btn btn-${variant}${className ? ` ${className}` : ""}`}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
    >
      {busy ? "Đang xử lý…" : children}
    </button>
  );
}

export function ErrorBox({ error }: { error: unknown }) {
  if (!error) return null;
  return (
    <div className="alert alert-danger" role="alert">
      {errorMessage(error)}
    </div>
  );
}

export function Notice({ tone = "info", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <div className={`alert alert-${tone}`} role="status">
      {children}
    </div>
  );
}

export function Loading({ label = "Đang tải…" }: { label?: string }) {
  return (
    <p className="loading-state muted" aria-busy="true">
      <span className="loading-orbit" aria-hidden="true" />{label}
    </p>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="empty"><span className="empty-compass" aria-hidden="true">✦</span>{children}</p>;
}

export function Field({ label, hint, children }: { label: string; hint?: ReactNode; children: ReactNode }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint ? <span className="field-hint">{hint}</span> : null}
    </label>
  );
}

export function PageHeader({ title, sub, actions }: { title: ReactNode; sub?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        {sub ? <p className="muted">{sub}</p> : null}
      </div>
      {actions ? <div className="page-actions">{actions}</div> : null}
    </header>
  );
}

export function DataNotice() {
  return <p className="data-notice"><span aria-hidden="true">ⓘ</span> DỮ LIỆU MINH HỌA — số liệu trong môi trường thử nghiệm là giả.</p>;
}
