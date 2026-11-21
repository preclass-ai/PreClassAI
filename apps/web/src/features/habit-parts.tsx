export function HabitMark() {
  return (
    <svg className="habit-mark" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
      <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="M12 6l1.6 4.4L18 12l-4.4 1.6L12 18l-1.6-4.4L6 12l4.4-1.6z" fill="currentColor" />
    </svg>
  );
}

export function SourceRef({ label, excerpt }: { label: string; excerpt: string }) {
  return (
    <blockquote className="habit-source">
      <span className="habit-source-label">Nguồn đã được thầy cô duyệt · {label}</span>
      {excerpt}
    </blockquote>
  );
}

export function HintIcon() {
  return (
    <svg className="habit-mark" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 18h6M10 21h4" />
      <path d="M12 3a6 6 0 0 0-3.6 10.8c.6.5 1.1 1.3 1.1 2.2h5c0-.9.5-1.7 1.1-2.2A6 6 0 0 0 12 3z" />
    </svg>
  );
}
