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
