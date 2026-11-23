import { useId } from "react";

/** "Bé Cầu": the PreClass AI logo (globe + location dot) with a face and the sprout of the app icon. Teachers' guide. */
export const GUIDE_NAME = "Bé Cầu";
export const GUIDE_ACCENT = "#0b8f8a";

export function GlobeMascot({ size = 36, className }: { size?: number; className?: string }) {
  const id = useId().replace(/:/g, "");
  return (
    <span
      className={`mascot-avatar globe-mascot${className ? ` ${className}` : ""}`}
      style={{ width: size, height: size, ["--mascot" as string]: GUIDE_ACCENT }}
      aria-hidden="true"
    >
      <svg viewBox="0 0 64 64" width="100%" height="100%">
        <defs>
          <radialGradient id={`f${id}`} cx="40%" cy="35%" r="70%">
            <stop offset="0" stopColor="#ffffff" />
            <stop offset="1" stopColor="#d4f3ec" />
          </radialGradient>
          <linearGradient id={`l${id}`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#c8ec8f" />
            <stop offset="1" stopColor="#7cc95a" />
          </linearGradient>
        </defs>
        <path d="M38 17c0-4 1-7 3-9" stroke="#5aa64a" strokeWidth="2.2" fill="none" strokeLinecap="round" />
        <path d="M41 9c1-5 6-7 12-6-1 6-6 8-12 6z" fill={`url(#l${id})`} />
        <path d="M40 10c-2-4-6-6-11-5 1 5 5 7 11 5z" fill={`url(#l${id})`} />
        <circle cx="32" cy="37" r="22" fill={`url(#f${id})`} stroke="#0b6c80" strokeWidth="2.6" />
        <path d="M10 37h44M32 15c7 6 10 13 10 22s-3 16-10 22M32 15c-7 6-10 13-10 22s3 16 10 22" stroke="#0b6c80" strokeWidth="2" fill="none" opacity="0.32" />
        <circle cx="45.5" cy="21" r="4.6" fill="#0b6c80" />
        <circle cx="44.2" cy="19.7" r="1.3" fill="#fff" />
        <ellipse cx="24.5" cy="38" rx="2.7" ry="3.4" fill="#0e3c46" />
        <ellipse cx="39.5" cy="38" rx="2.7" ry="3.4" fill="#0e3c46" />
        <circle cx="25.4" cy="36.8" r="1" fill="#fff" />
        <circle cx="40.4" cy="36.8" r="1" fill="#fff" />
        <ellipse cx="19" cy="44" rx="3.4" ry="2.1" fill="#f6a5b8" opacity="0.75" />
        <ellipse cx="45" cy="44" rx="3.4" ry="2.1" fill="#f6a5b8" opacity="0.75" />
        <path d="M28 44.5c2.4 2.8 5.6 2.8 8 0" stroke="#0e3c46" strokeWidth="2.2" fill="none" strokeLinecap="round" />
      </svg>
    </span>
  );
}
