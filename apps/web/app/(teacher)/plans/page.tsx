"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";
import { Badge, Button, Empty, ErrorBox, Loading, Notice, PageHeader } from "@/components/ui";
import { api, postForm, unwrap, type Schemas } from "@/lib/api";
import { fmtDate } from "@/lib/format";

export default function PlansPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const file = useRef<HTMLInputElement>(null);
  const list = useQuery({
    queryKey: ["plans"],
    queryFn: () => unwrap(api.GET("/v1/lesson-plans")),
    refetchInterval: (q) => (q.state.data?.items.some((p) => p.aiState === "queued" || p.aiState === "running") ? 2500 : false),
  });
  // The reading runs on the server as a job: it survives a reload and we resume from the latest job.
  const latest = useQuery({
    queryKey: ["plan-job"],
    queryFn: () => unwrap(api.GET("/v1/lesson-plans/jobs/latest")),
    refetchInterval: (q) => {
      const st = q.state.data?.job?.state;
      return st === "queued" || st === "parsing" ? 1500 : false;
    },
  });
  const job = latest.data?.job ?? null;
  const active = job?.state === "queued" || job?.state === "parsing";
  const waiting = useRef<string | null>(null); // the job this tab is waiting for: go to the check screen when it ends
  const upload = useMutation({
    mutationFn: (f: File) => {
      const form = new FormData();
      form.append("file", f);
      return postForm<Schemas["PlanJobOut"]>("/v1/lesson-plans", form);
    },
    onSuccess: async (j) => {
      waiting.current = j.id;
      await qc.invalidateQueries({ queryKey: ["plan-job"] });
    },
  });
  useEffect(() => {
    if (active && job) waiting.current = job.id;
    if (job?.state === "done" && waiting.current === job.id) {
      waiting.current = null;
      void qc.invalidateQueries({ queryKey: ["plans"] });
      if (job.planIds.length === 1) router.push(`/plans/${job.planIds[0]}`);
    }
  }, [active, job, qc, router]);

  return (
    <div className="stack">
      <PageHeader title="Giáo án" sub="Nạp giáo án (DOCX hoặc PDF có chữ). Hệ thống đọc ra mục tiêu, 4 hoạt động và câu trắc nghiệm để thầy cô kiểm tra rồi tạo bài chuẩn bị trước giờ học." />
      <section className="card stack">
        <label htmlFor="plan-file">Chọn tệp giáo án</label>
        <input id="plan-file" ref={file} type="file" accept=".docx,.pdf" />
        <Button
          variant="primary"
          busy={upload.isPending}
          disabled={active}
          onClick={() => {
            const f = file.current?.files?.[0];
            if (f) upload.mutate(f);
          }}
        >
          Đọc giáo án
        </Button>
        {active && job ? (
          <div role="status" aria-live="polite" className="stack">
            <Notice>
              {job.state === "queued" ? "Giáo án đang chờ đến lượt đọc…" : job.page && job.pages ? `Đang đọc giáo án… trang ${job.page}/${job.pages}` : "Đang đọc giáo án…"}
            </Notice>
            <progress max={job.pages ?? 1} value={job.state === "parsing" && job.pages ? (job.page ?? 0) : undefined} aria-label="Tiến trình đọc giáo án" />
            <p className="muted small">Thầy cô có thể tải lại trang hoặc làm việc khác, hệ thống vẫn đọc tiếp.</p>
          </div>
        ) : null}
        {job?.state === "failed" ? <Notice tone="warning">{job.errorTitle ?? "Chưa đọc được giáo án này."}</Notice> : null}
        <ErrorBox error={upload.error} />
        <p className="muted small">Tên giáo viên và chữ ký được loại bỏ khi đọc. Đáp án câu trắc nghiệm chỉ lấy từ chữ cái được gạch chân; câu không có gạch chân thầy cô chọn tay.</p>
      </section>
      {list.isPending ? <Loading /> : list.data?.items.length ? (
        <ul className="plain stack">
          {list.data.items.map((p) => (
            <li key={p.id} className="card">
              <Link href={`/plans/${p.id}`}>
                <strong>{p.title}</strong>
              </Link>{" "}
              {p.lessonId ? <Badge tone="success">Đã tạo bài</Badge> : null}
              <div className="muted small">
                {p.ppctPeriod ? `Tiết ${p.ppctPeriod}` : ""} {p.taughtFrom ? `· dạy ${fmtDate(p.taughtFrom)}` : ""} · {p.mcqCount} câu trắc nghiệm, {p.needsConfirmationCount} cần xác nhận
              </div>
              {p.aiState === "queued" || p.aiState === "running" ? (
                <div className="small" role="status">
                  Đang soạn câu hỏi…
                </div>
              ) : p.aiQuizCount + p.aiReviewCount > 0 ? (
                <div className="small">
                  {p.aiQuizCount} câu AI soạn, {p.aiQuizNeedsConfirmationCount} cần xác nhận. {p.aiReviewCount} thẻ ôn.
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <Empty>Chưa có giáo án nào.</Empty>
      )}
    </div>
  );
}
