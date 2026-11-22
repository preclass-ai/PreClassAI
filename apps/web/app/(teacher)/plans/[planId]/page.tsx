"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { NextStep } from "@/components/next-step";
import { Badge, Button, ErrorBox, Loading, Notice, PageHeader } from "@/components/ui";
import { api, unwrap } from "@/lib/api";
import { AiDrafts } from "@/features/ai-drafts";
import { fmtDate } from "@/lib/format";

const ACTIVITY: Record<string, string> = { mo_dau: "Mở đầu", hinh_thanh: "Hình thành kiến thức", luyen_tap: "Luyện tập", van_dung: "Vận dụng" };
const TYPE: Record<string, string> = { knowledge_box: "Khung kiến thức", table_cell: "Bảng", figure_caption: "Chú thích hình" };

export default function PlanPage() {
  const { planId } = useParams<{ planId: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const path = { plan_id: planId };
  const plan = useQuery({
    queryKey: ["plan", planId],
    queryFn: () => unwrap(api.GET("/v1/lesson-plans/{plan_id}", { params: { path } })),
    refetchInterval: (q) => (q.state.data?.aiState === "queued" || q.state.data?.aiState === "running" ? 2000 : false),
  });
  const confirm = useMutation({
    mutationFn: (v: { mcq: string; option: "A" | "B" | "C" | "D" }) =>
      unwrap(api.PUT("/v1/lesson-plans/{plan_id}/mcqs/{mcq_id}/answer", { params: { path: { plan_id: planId, mcq_id: v.mcq } }, body: { correctOption: v.option } })),
    onSuccess: (d) => qc.setQueryData(["plan", planId], d),
  });
  const competency = useMutation({
    mutationFn: (v: { mcq: string; code: string | null }) =>
      unwrap(api.PUT("/v1/lesson-plans/{plan_id}/mcqs/{mcq_id}/competency", { params: { path: { plan_id: planId, mcq_id: v.mcq } }, body: { competencyCode: v.code } })),
    onSuccess: (d) => qc.setQueryData(["plan", planId], d),
  });
  const build = useMutation({
    mutationFn: () => unwrap(api.POST("/v1/lesson-plans/{plan_id}/lesson", { params: { path } })),
    onSuccess: async (r) => {
      await qc.invalidateQueries({ queryKey: ["plans"] });
      router.push(`/lessons/${r.lessonId}?tab=editor`);
    },
  });
  if (plan.isPending) return <Loading />;
  if (!plan.data) return <ErrorBox error={plan.error} />;
  const p = plan.data;

  return (
    <div className="stack">
      <PageHeader
        title={p.title}
        sub={`${p.ppctPeriod ? `Tiết ${p.ppctPeriod}` : "Chưa có tiết PPCT"}${p.week ? ` · Tuần ${p.week}` : ""}${p.taughtFrom ? ` · Dạy ${fmtDate(p.taughtFrom)}` : ""}`}
        actions={<Link href="/plans">Tất cả giáo án</Link>}
      />
      <Notice>
        {p.suggestedDueAt
          ? `Gợi ý hạn nộp: ${fmtDate(p.suggestedDueAt)} (trước ngày dạy 1 ngày). Thầy cô đặt hạn khi giao bài.`
          : "Giáo án không ghi ngày dạy. Thầy cô chọn ngày học khi giao bài."}{" "}
        Đã loại {p.redactedCount} đoạn có tên hoặc chữ ký.
      </Notice>

      <section className="card stack" aria-labelledby="obj">
        <h2 id="obj">Mục tiêu</h2>
        {p.objectives.length === 0 ? <p className="muted">Chưa đọc được mục tiêu.</p> : (
          <ul>
            {p.objectives.map((o, i) => (
              <li key={i}>
                {o.text} {o.competencyName ? <Badge tone="info">{o.competencyName}</Badge> : null}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card stack" aria-labelledby="act">
        <h2 id="act">Các hoạt động đã nhận ra</h2>
        <p>
          {(["mo_dau", "hinh_thanh", "luyen_tap", "van_dung"] as const).map((a) => (
            <Badge key={a} tone={p.activities.includes(a) ? "success" : "warning"}>
              {ACTIVITY[a]}
              {p.activities.includes(a) ? "" : ": chưa thấy"}
            </Badge>
          ))}
        </p>
        {p.sections.filter((s) => s.kind === "activity").map((s, i) => (
          <details key={i}>
            <summary>
              {s.activityType ? ACTIVITY[s.activityType] : "Hoạt động"} ({s.items.length} đoạn)
            </summary>
            <ul className="plain">
              {s.items.slice(0, 12).map((it) => (
                <li key={it.anchorId} className="small">
                  {it.type !== "paragraph" && it.type !== "heading" ? <Badge>{TYPE[it.type] ?? it.type}</Badge> : null} {it.text.slice(0, 200)}
                  {it.page ? <span className="muted"> (trang {it.page})</span> : null}
                </li>
              ))}
            </ul>
          </details>
        ))}
      </section>

      <section className="card stack" aria-labelledby="mcq">
        <h2 id="mcq">Câu trắc nghiệm ({p.mcqs.length})</h2>
        {p.needsConfirmationCount > 0 ? <Notice tone="warning">{p.needsConfirmationCount} câu chưa rõ đáp án. Chọn đáp án đúng cho từng câu; câu chưa chọn sẽ không vào bài.</Notice> : null}
        <ErrorBox error={confirm.error} />
        <ErrorBox error={competency.error} />
        {p.mcqs.map((q) => (
          <fieldset key={q.id} className="stack">
            <legend>
              Câu {q.position}. {q.stem}{" "}
              {q.needsConfirmation ? <Badge tone="warning">Cần xác nhận</Badge> : <Badge tone="success">{q.answerSource === "teacher" ? "Thầy cô chọn" : "Từ gạch chân"}</Badge>}
            </legend>
            {q.options.map((o) => (
              <label key={o.label}>
                <input type="radio" name={`q-${q.id}`} checked={q.correctOption === o.label} onChange={() => confirm.mutate({ mcq: q.id, option: o.label })} /> {o.label}. {o.text}
              </label>
            ))}
            {p.competencies.length ? (
              <label className="small">
                Năng lực (không bắt buộc){" "}
                <select value={q.competencyCode ?? ""} onChange={(e) => competency.mutate({ mcq: q.id, code: e.target.value || null })}>
                  <option value="">Không bắt buộc</option>
                  {p.competencies.map((c) => (
                    <option key={c.code} value={c.code}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
          </fieldset>
        ))}
      </section>

      <AiDrafts plan={p} />

      <section className="card stack">
        {p.lessonId ? (
          <NextStep label="Tiếp: Soạn bài" href={`/lessons/${p.lessonId}?tab=editor`} />
        ) : (
          <>
            <Button variant="primary" busy={build.isPending} onClick={() => build.mutate()}>
              Tạo bài chuẩn bị trước giờ học
            </Button>
            <p className="muted small">Tạo bản nháp: câu khơi gợi, thẻ đọc trước, tối đa 5 câu luyện tập đã có đáp án, các câu và thẻ ôn do AI soạn mà thầy cô đã Duyệt, nhiệm vụ vận dụng. Thầy cô duyệt từng khối rồi mới xuất bản.</p>
          </>
        )}
        <ErrorBox error={build.error} />
      </section>
    </div>
  );
}
