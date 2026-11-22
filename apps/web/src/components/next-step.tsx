import Link from "next/link";
import { Button } from "./ui";

/** End-of-step button of the teacher flow (Nguồn → Soạn bài → Duyệt → Xuất bản → Giao bài).
 * When the step is not finished it stays visible but disabled, with the reason next to it. */
export function NextStep({ label, href, blockedBy }: { label: string; href: string; blockedBy?: string | null }) {
  return (
    <div className="next-step row-actions">
      {blockedBy ? (
        <>
          <Button variant="primary" disabled aria-describedby="next-step-why">
            {label}
          </Button>
          <span className="muted small" id="next-step-why">
            {blockedBy}
          </span>
        </>
      ) : (
        <Link className="btn btn-primary" href={href}>
          {label}
        </Link>
      )}
    </div>
  );
}
