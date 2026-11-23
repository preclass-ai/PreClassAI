"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge, Button, ErrorBox, Loading, Notice } from "@/components/ui";
import { api, unwrap, type Schemas } from "@/lib/api";

type Item = Schemas["PlanAiItemOut"];
type Plan = Schemas["PlanDetail"];
const LETTERS = ["A", "B", "C", "D"];
const LEVELS: Record<string, string> = { NHAN_BIET: "Nhận biết", THONG_HIEU: "Thông hiểu", VAN_DUNG: "Vận dụng" };
const OPS: Record<string, string> = { sum: "Tổng", diff: "Hiệu (số đầu trừ các số sau)", ratio: "Thương (số đầu chia số thứ hai)", percent: "Tỉ lệ phần trăm (số đầu chia số thứ hai, nhân 100)" };
const MAX_TOTAL = 8; // QUIZ_GEN_PER_LESSON default; the server answers QUIZ_COUNT when its own limit is lower
const vn = (n: unknown) => String(n).replace(".", ",");
const STATUS: Record<Item["status"], { tone: "info" | "success" | "warning"; label: string }> = {
  draft: { tone: "warning", label: "Cần xác nhận" },
  approved: { tone: "success", label: "Đã duyệt" },
  rejected: { tone: "info", label: "Đã loại" },
};

/** Why the model did not draft anything (stats.reason), in words a teacher can act on. */
function reasonText(p: Plan): string | null {
  if (p.aiState === "failed") return "AI chưa soạn được câu hỏi cho giáo án này. Thầy cô bấm Tạo lại câu hỏi để thử lần nữa.";
  if (p.aiState !== "skipped") return null;
  const r = (p.aiStats as { reason?: string } | null)?.reason;
  if (r === "budget") return "Hôm nay AI đã dùng hết hạn mức soạn câu hỏi. Thầy cô thử lại vào ngày mai.";
  if (r === "too_short") return "Giáo án quá ngắn để AI soạn câu hỏi.";
  return "AI soạn câu hỏi chưa được bật.";
}

export function AiDrafts({ plan }: { plan: Plan }) {
  const qc = useQueryClient();
  const planId = plan.id;
  const [tab, setTab] = useState<"quiz" | "review">("quiz");
  const busy = plan.aiState === "queued" || plan.aiState === "running";
  const list = useQuery({
    queryKey: ["plan-ai", planId],
    queryFn: () => unwrap(api.GET("/v1/lesson-plans/{plan_id}/ai-items", { params: { path: { plan_id: planId } } })),
    refetchInterval: busy ? 2000 : false,
  });
  const refresh = () => {
    void qc.invalidateQueries({ queryKey: ["plan-ai", planId] });
    void qc.invalidateQueries({ queryKey: ["plan", planId] });
    void qc.invalidateQueries({ queryKey: ["plans"] });
  };
  const [mcq, setMcq] = useState(6);
  const [numeric, setNumeric] = useState(2);
  const [level, setLevel] = useState("");
  const total = mcq + numeric;
  const regen = useMutation({
    mutationFn: () =>
      unwrap(
        api.POST("/v1/lesson-plans/{plan_id}/ai-items/regenerate", {
          params: { path: { plan_id: planId } },
          body: { mcq, numeric, level: (level || null) as Schemas["PlanAiRegenerate"]["level"] },
        }),
      ),
    onSuccess: refresh,
  });
  const items = (list.data?.items ?? []).filter((i) => i.kind === tab);
  const counts = { quiz: plan.aiQuizCount, review: plan.aiReviewCount };
  const hint = reasonText(plan);
  const tabFailed = (plan.aiStats as Record<string, { failed?: boolean } | null> | null)?.[tab]?.failed === true;
  const locked = !!plan.lessonId; // after "Tạo bài chuẩn bị" the drafts are frozen: edit the lesson itself

  return (
    <section className="card stack" aria-labelledby="ai-title">
      <h2 id="ai-title">AI soạn từ giáo án</h2>
      {busy ? (
        <div role="status" aria-live="polite" className="stack">
          <Notice>Đang soạn câu hỏi và thẻ ôn từ giáo án…</Notice>
          <progress aria-label="AI đang soạn" />
        </div>
      ) : null}
      {hint ? <Notice tone="warning">{hint}</Notice> : null}
      {plan.aiState === "done" ? (
        <p className="muted small">
          {plan.aiQuizCount} câu AI soạn, {plan.aiQuizNeedsConfirmationCount} cần xác nhận. {plan.aiReviewCount} thẻ ôn. Chỉ mục đã Duyệt mới vào bài chuẩn bị, và mọi đáp án do AI soạn cần thầy cô xác nhận.
        </p>
      ) : null}
      <div role="tablist" aria-label="Loại nội dung AI soạn" className="row">
        {(["quiz", "review"] as const).map((t) => (
          <button key={t} role="tab" type="button" aria-selected={tab === t} className={tab === t ? "btn btn-primary" : "btn btn-secondary"} onClick={() => setTab(t)}>
            {t === "quiz" ? `Câu hỏi (${counts.quiz})` : `Ôn tập (${counts.review})`}
          </button>
        ))}
      </div>
      <ErrorBox error={list.error ?? regen.error} />
      {list.isPending ? <Loading /> : null}
      {!list.isPending && items.length === 0 && !busy ? (
        <Notice tone={tabFailed ? "warning" : "info"}>
          {tabFailed
            ? `${tab === "quiz" ? "Chưa soạn được câu hỏi" : "Chưa soạn được thẻ ôn"} cho giáo án này. Các phần khác vẫn được giữ. Thầy cô bấm Tạo lại câu hỏi để thử lần nữa.`
            : "Chưa có mục nào."}
        </Notice>
      ) : null}
      {items.map((it) => (
        <AiItemCard key={`${it.id}-${it.status}-${JSON.stringify(it.payload).length}`} planId={planId} item={it} locked={locked} onChange={refresh} />
      ))}
      {!locked ? (
        <fieldset className="stack" disabled={busy}>
          <legend className="small">Chọn dạng câu theo cấu trúc đề tốt nghiệp THPT</legend>
          <div className="row">
            <label className="stack">
              <span className="small">Phần I: trắc nghiệm nhiều lựa chọn</span>
              <input type="number" min={0} max={MAX_TOTAL} value={mcq} onChange={(e) => setMcq(Math.max(0, Number(e.target.value) || 0))} />
            </label>
            <label className="stack">
              <span className="small">Phần III: trả lời ngắn bằng một số</span>
              <input type="number" min={0} max={MAX_TOTAL} value={numeric} onChange={(e) => setNumeric(Math.max(0, Number(e.target.value) || 0))} />
            </label>
            <label className="stack">
              <span className="small">Mức độ</span>
              <select value={level} onChange={(e) => setLevel(e.target.value)}>
                <option value="">Không gắn</option>
                {Object.entries(LEVELS).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <p className="muted small">
            Tổng {total} câu, không quá {MAX_TOTAL}. Phần II (đúng/sai 4 ý) chưa có. Số câu được tính cả các câu đã Duyệt giữ lại.
          </p>
          <Button busy={regen.isPending} disabled={busy || total === 0 || total > MAX_TOTAL} onClick={() => regen.mutate()}>
            Tạo lại câu hỏi
          </Button>
        </fieldset>
      ) : null}
      {!locked ? <p className="muted small">Mục đã Duyệt được giữ lại, các mục còn lại được soạn mới.</p> : null}
    </section>
  );
}

function AiItemCard({ planId, item, locked, onChange }: { planId: string; item: Item; locked: boolean; onChange: () => void }) {
  const [editing, setEditing] = useState(false);
  const act = useMutation({
    mutationFn: (body: Schemas["PlanAiItemUpdate"]) =>
      unwrap(api.PATCH("/v1/lesson-plans/{plan_id}/ai-items/{item_id}", { params: { path: { plan_id: planId, item_id: item.id } }, body })),
    onSuccess: () => {
      setEditing(false);
      onChange();
    },
  });
  const p = item.payload as Record<string, unknown>;
  const st = STATUS[item.status];
  return (
    <article className="card stack" aria-label={item.kind === "quiz" ? "Câu hỏi AI soạn" : "Thẻ ôn AI soạn"}>
      <div className="row">
        <Badge tone="info">AI soạn</Badge> <Badge tone={st.tone}>{st.label}</Badge>
        {item.kind === "quiz" ? <Badge tone="info">{p.item_type === "NUMERIC" ? "Phần III: trả lời số" : "Phần I: trắc nghiệm"}</Badge> : null}
        {typeof p.level === "string" && LEVELS[p.level] ? <Badge tone="info">{LEVELS[p.level]}</Badge> : null}
      </div>
      {editing ? (
        <ItemForm item={item} busy={act.isPending} onCancel={() => setEditing(false)} onSave={(payload) => act.mutate({ payload })} />
      ) : item.kind === "quiz" ? (
        <QuizView p={p} />
      ) : (
        <CardView p={p} />
      )}
      <blockquote className="source-quote">
        <span className="muted small">Trích từ giáo án</span>
        <br />
        {item.sourceQuote}
      </blockquote>
      <ErrorBox error={act.error} />
      {!locked && !editing ? (
        <div className="row">
          <Button onClick={() => setEditing(true)}>Sửa</Button>
          <Button variant="primary" busy={act.isPending} disabled={item.status === "approved"} onClick={() => act.mutate({ status: "approved" })}>
            Duyệt
          </Button>
          <Button disabled={item.status === "rejected"} onClick={() => act.mutate({ status: "rejected" })}>
            Loại
          </Button>
        </div>
      ) : null}
    </article>
  );
}

function QuizView({ p }: { p: Record<string, unknown> }) {
  if (p.item_type === "NUMERIC") return <NumericView p={p} />;
  const options = (p.options as string[]) ?? [];
  const right = Number(p.correct_index);
  return (
    <div className="stack">
      <p>
        <strong>{String(p.stem)}</strong>
      </p>
      <ul className="plain">
        {options.map((o, i) => (
          <li key={i}>
            {LETTERS[i]}. {o} {i === right ? <Badge tone="success">Đáp án AI chọn</Badge> : null}
          </li>
        ))}
      </ul>
      <p className="small">Giải thích: {String(p.explanation)}</p>
      <details>
        <summary className="small">3 gợi ý cố định</summary>
        <ol className="small">
          {((p.hints as string[]) ?? []).map((h, i) => (
            <li key={i}>{h}</li>
          ))}
        </ol>
      </details>
    </div>
  );
}

/** Part III: the answer shown is the one the server worked out from the operands, not the model's own claim. */
function NumericView({ p }: { p: Record<string, unknown> }) {
  const operands = ((p.operands as number[]) ?? []).map(vn).join("; ");
  return (
    <div className="stack">
      <p>
        <strong>{String(p.stem)}</strong>
      </p>
      <p className="small">
        Đáp án (máy tính lại): <strong>{vn(p.answer)}</strong> {String(p.unit)} <Badge tone="success">Phép tính khớp</Badge>
      </p>
      <p className="small">
        Phép tính: {OPS[String(p.op)] ?? String(p.op)} của {operands}
      </p>
      <p className="small">Giải thích: {String(p.explanation)}</p>
      <details>
        <summary className="small">3 gợi ý cố định</summary>
        <ol className="small">
          {((p.hints as string[]) ?? []).map((h, i) => (
            <li key={i}>{h}</li>
          ))}
        </ol>
      </details>
    </div>
  );
}

function CardView({ p }: { p: Record<string, unknown> }) {
  const c = p.check as { statement: string; answer_true: boolean; explanation: string };
  return (
    <div className="stack">
      <p>
        <strong>{String(p.title)}</strong>
      </p>
      <ul>
        {((p.points as string[]) ?? []).map((x, i) => (
          <li key={i}>{x}</li>
        ))}
      </ul>
      <p className="small">Ví dụ: {String(p.example)}</p>
      <p className="small">
        Tự kiểm tra: {c.statement} ({c.answer_true ? "Đúng" : "Sai"}). {c.explanation}
      </p>
    </div>
  );
}

/** Edit form: plain fields; the server validates the whole item again (4 options, 3 hints, quote). */
function ItemForm({ item, busy, onSave, onCancel }: { item: Item; busy: boolean; onSave: (p: Record<string, unknown>) => void; onCancel: () => void }) {
  const [v, setV] = useState<Record<string, unknown>>(() => structuredClone(item.payload as Record<string, unknown>));
  const set = (k: string, val: unknown) => setV((x) => ({ ...x, [k]: val }));
  const arr = (k: string) => (v[k] as string[]) ?? [];
  const setAt = (k: string, i: number, val: string) => set(k, arr(k).map((x, j) => (j === i ? val : x)));
  const check = (v.check as { statement: string; answer_true: boolean; explanation: string } | undefined) ?? { statement: "", answer_true: true, explanation: "" };
  const field = (label: string, value: string, on: (s: string) => void, rows = 1) => (
    <label className="stack">
      <span className="small">{label}</span>
      {rows > 1 ? <textarea rows={rows} value={value} onChange={(e) => on(e.target.value)} /> : <input value={value} onChange={(e) => on(e.target.value)} />}
    </label>
  );
  return (
    <form
      className="stack"
      onSubmit={(e) => {
        e.preventDefault();
        onSave({ ...v, source_quote: item.sourceQuote });
      }}
    >
      {item.kind === "quiz" && v.item_type === "NUMERIC" ? (
        <>
          {field("Câu hỏi (nêu đủ số liệu cần dùng)", String(v.stem ?? ""), (s) => set("stem", s), 3)}
          <label className="stack">
            <span className="small">Phép tính</span>
            <select value={String(v.op)} onChange={(e) => set("op", e.target.value)}>
              {Object.entries(OPS).map(([k, label]) => (
                <option key={k} value={k}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          {field("Các số (cách nhau bằng dấu chấm phẩy, đều phải có trong đoạn trích)", ((v.operands as number[]) ?? []).map(vn).join("; "),
            (s) => set("operands", s.split(";").map((x) => Number(x.trim().replace(",", "."))).filter((x) => !Number.isNaN(x))))}
          {field("Đơn vị", String(v.unit ?? ""), (s) => set("unit", s))}
          <p className="muted small">Đáp án do máy tính lại từ các số và phép tính khi lưu.</p>
          {field("Giải thích", String(v.explanation ?? ""), (s) => set("explanation", s), 2)}
          {arr("hints").map((h, i) => field(`Gợi ý ${i + 1}`, h, (s) => setAt("hints", i, s)))}
        </>
      ) : item.kind === "quiz" ? (
        <>
          {field("Câu hỏi", String(v.stem ?? ""), (s) => set("stem", s), 2)}
          {arr("options").map((o, i) => field(`Phương án ${LETTERS[i]}`, o, (s) => setAt("options", i, s)))}
          <label className="stack">
            <span className="small">Đáp án đúng</span>
            <select value={Number(v.correct_index)} onChange={(e) => set("correct_index", Number(e.target.value))}>
              {LETTERS.map((l, i) => (
                <option key={l} value={i}>
                  {l}
                </option>
              ))}
            </select>
          </label>
          {field("Giải thích", String(v.explanation ?? ""), (s) => set("explanation", s), 2)}
          {arr("hints").map((h, i) => field(`Gợi ý ${i + 1}`, h, (s) => setAt("hints", i, s)))}
        </>
      ) : (
        <>
          {field("Tiêu đề", String(v.title ?? ""), (s) => set("title", s))}
          {field("Ý chính (mỗi dòng một ý, 2 đến 4 ý)", arr("points").join("\n"), (s) => set("points", s.split("\n").filter((x) => x.trim())), 4)}
          {field("Ví dụ hoặc số liệu", String(v.example ?? ""), (s) => set("example", s), 2)}
          {field("Câu tự kiểm tra", check.statement, (s) => set("check", { ...check, statement: s }), 2)}
          <label>
            <input type="checkbox" checked={check.answer_true} onChange={(e) => set("check", { ...check, answer_true: e.target.checked })} /> Câu này đúng
          </label>
          {field("Giải thích ngay", check.explanation, (s) => set("check", { ...check, explanation: s }), 2)}
        </>
      )}
      {item.kind === "quiz" ? (
        <label className="stack">
          <span className="small">Mức độ (nhãn gợi ý)</span>
          <select value={String(v.level ?? "")} onChange={(e) => set("level", e.target.value || null)}>
            <option value="">Không gắn</option>
            {Object.entries(LEVELS).map(([k, label]) => (
              <option key={k} value={k}>
                {label}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      <div className="row">
        <Button type="submit" variant="primary" busy={busy}>
          Lưu
        </Button>
        <Button type="button" onClick={onCancel}>
          Hủy
        </Button>
      </div>
    </form>
  );
}
