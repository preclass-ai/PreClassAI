import { useState } from "react";
import { createApiClient, type ApiClient } from "@preclass/api-client";

/* Dev console: a reference for the API contract, NOT the product UI.
   Every call shows the raw JSON. Routes that still answer 501 are re-sent to the Prism mock (/mock) and tagged MOCK. */

const real = createApiClient();
const mock = createApiClient({ baseUrl: "/mock" });

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type J = any;
type Result = { data?: J; error?: J; response: Response };
type Shown = { label: string; mock: boolean; status: number; body: J };

async function call(label: string, fn: (c: ApiClient) => Promise<Result>): Promise<Shown> {
  let r = await fn(real);
  let isMock = false;
  if (r.response.status === 501) {
    r = await fn(mock);
    isMock = true;
  }
  return { label, mock: isMock, status: r.response.status, body: r.data ?? r.error };
}

const SEED = [
  ["GV Địa lí", "gv.dia@preclass.local"],
  ["GV khác", "gv.khac@preclass.local"],
  ["Reviewer", "reviewer@preclass.local"],
  ["HS10-01", "HS10-01"],
  ["Admin", "admin@preclass.local"],
] as const;

type Block = { id: string; kind: string; parentId: string | null; position: number; payload: J; reviewStatus: string; transformation: string; contentHash: string };

function Tree({ blocks, onPick }: { blocks: Block[]; onPick: (b: Block) => void }) {
  const kids = (pid: string | null) => blocks.filter((b) => b.parentId === pid).sort((a, b) => a.position - b.position);
  const node = (b: Block): J => (
    <li key={b.id}>
      <span className="link" onClick={() => onPick(b)}>
        {b.kind}: {b.payload?.text ?? b.payload?.stem ?? b.payload?.label ?? JSON.stringify(b.payload)}
      </span>
      <span className={`tag ${b.reviewStatus}`}>{b.reviewStatus}</span>
      <span className="tag">{b.transformation}</span>
      <ul className="tree">{kids(b.id).map(node)}</ul>
    </li>
  );
  return <ul className="tree">{kids(null).map(node)}</ul>;
}

export function App() {
  const [tab, setTab] = useState("login");
  const [out, setOut] = useState<Shown | null>(null);
  const [lessons, setLessons] = useState<J[]>([]);
  const [revId, setRevId] = useState("");
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [queue, setQueue] = useState<Block[]>([]);
  const [prov, setProv] = useState<J>(null);
  const [assigns, setAssigns] = useState<J[]>([]);
  const [work, setWork] = useState<J>(null);
  const [answers, setAnswers] = useState<Record<string, J>>({});

  const show = async (label: string, fn: (c: ApiClient) => Promise<Result>) => {
    const r = await call(label, fn);
    setOut(r);
    return r;
  };

  const Tabs = (
    <nav>
      {[["login", "1 Đăng nhập"], ["lessons", "2 GV: bài → block"], ["prov", "3 Provenance"], ["queue", "4 Review queue"], ["student", "5 HS"]].map(([k, t]) => (
        <button key={k} className={tab === k ? "on" : ""} onClick={() => setTab(k!)}>{t}</button>
      ))}
    </nav>
  );

  return (
    <>
      <div className="banner">Dev console — dữ liệu minh họa — không phải giao diện sản phẩm</div>
      <main>
        {Tabs}
        <div className="row">
          <div className="col">
            {tab === "login" && (
              <>
                <h2>Đăng nhập nhanh (mật khẩu seed)</h2>
                {SEED.map(([name, id]) => (
                  <button key={id} onClick={() => show(`login ${id}`, (c) => c.POST("/v1/auth/login", { body: { identifier: id, password: "preclass-demo" } }))}>{name}</button>
                ))}
                <p>
                  <button onClick={() => show("me", (c) => c.GET("/v1/me"))}>GET /me</button>
                  <button onClick={() => show("classes", (c) => c.GET("/v1/classes"))}>GET /classes (GV)</button>
                  <button onClick={() => show("logout", (c) => c.POST("/v1/auth/logout"))}>Đăng xuất</button>
                </p>
              </>
            )}
            {tab === "lessons" && (
              <>
                <h2>Bài giảng</h2>
                <button onClick={async () => setLessons((await show("lessons", (c) => c.GET("/v1/lessons"))).body?.items ?? [])}>Tải danh sách</button>
                <ul>
                  {lessons.map((l) => (
                    <li key={l.id}>
                      <span className="link" onClick={async () => {
                        const id = l.currentRevision.id as string;
                        setRevId(id);
                        setBlocks((await show(`blocks ${id}`, (c) => c.GET("/v1/revisions/{revision_id}/blocks", { params: { path: { revision_id: id } } }))).body?.items ?? []);
                      }}>{l.title} (lớp {l.grade}, rev {l.currentRevision.revisionNo}, {l.currentRevision.state})</span>
                    </li>
                  ))}
                </ul>
                {revId && <p>revision: <code>{revId}</code></p>}
                <Tree blocks={blocks} onPick={async (b) => {
                  setProv((await show(`provenance ${b.id}`, (c) => c.GET("/v1/blocks/{block_id}/provenance", { params: { path: { block_id: b.id } } }))).body);
                  setTab("prov");
                }} />
              </>
            )}
            {tab === "prov" && (
              <>
                <h2>Block → nguồn, kiểm tra, duyệt</h2>
                {!prov && <p>Chọn một block ở màn 2 hoặc 4.</p>}
                {prov && (
                  <>
                    <p><b>{prov.block.kind}</b> <span className={`tag ${prov.block.reviewStatus}`}>{prov.block.reviewStatus}</span> <span className="tag">{prov.block.transformation}</span></p>
                    <h2>Nguồn (có nguồn ≠ đúng)</h2>
                    <ul>{prov.links.map((l: J) => <li key={l.id}>[{l.anchor.code}] {l.anchor.kind} {JSON.stringify(l.anchor.locator)} “{l.anchor.excerpt}” <span className="tag">{l.status}</span></li>)}</ul>
                    <h2>Validation</h2>
                    <ul>{prov.validations.map((v: J) => <li key={v.id}>{v.rule} {v.severity} <b>{v.outcome}</b> {v.isCurrent ? "" : "(hash cũ)"}</li>)}</ul>
                    <h2>Lịch sử duyệt</h2>
                    <ul>{prov.reviews.map((r: J) => <li key={r.id}>{r.action} bởi {r.reviewerName} {r.isValid ? "(còn hiệu lực)" : "(hết hiệu lực)"}</li>)}</ul>
                    <button onClick={() => show("review APPROVE", (c) => c.POST("/v1/blocks/{block_id}/reviews", { params: { path: { block_id: prov.block.id } }, body: { action: "APPROVE", contentHash: prov.block.contentHash } }))}>Duyệt block này (APPROVE)</button>
                  </>
                )}
              </>
            )}
            {tab === "queue" && (
              <>
                <h2>Review queue</h2>
                <p>revision: <code>{revId || "(chọn bài ở màn 2; mock dùng id bất kỳ)"}</code></p>
                <button onClick={async () => setQueue((await show("review-queue", (c) => c.GET("/v1/revisions/{revision_id}/review-queue", { params: { path: { revision_id: revId || "00000000-0000-0000-0000-000000000001" } } }))).body?.items ?? [])}>Tải hàng đợi</button>
                <Tree blocks={queue.map((b) => ({ ...b, parentId: null }))} onPick={async (b) => {
                  setProv((await show(`provenance ${b.id}`, (c) => c.GET("/v1/blocks/{block_id}/provenance", { params: { path: { block_id: b.id } } }))).body);
                  setTab("prov");
                }} />
              </>
            )}
            {tab === "student" && (
              <>
                <h2>Học sinh (đăng nhập HS10-01 trước)</h2>
                <button onClick={async () => setAssigns((await show("student/assignments", (c) => c.GET("/v1/student/assignments"))).body?.items ?? [])}>Danh sách bài được giao</button>
                <ul>
                  {assigns.map((a) => (
                    <li key={a.id}>
                      <span className="link" onClick={async () => setWork((await show(`assignment ${a.id}`, (c) => c.GET("/v1/student/assignments/{assignment_id}", { params: { path: { assignment_id: a.id } } }))).body)}>{a.title} — {a.status}</span>
                    </li>
                  ))}
                </ul>
                {work && (
                  <>
                    {work.blocks.map((b: J) => <p key={b.id}>{b.payload.text ?? JSON.stringify(b.payload)}</p>)}
                    {work.items.map((it: J) => (
                      <div key={it.id}>
                        <p><b>{it.stem}</b></p>
                        {it.options.map((o: J) => (
                          <label key={o.label}><input type="radio" name={it.id} onChange={() => setAnswers({ ...answers, [it.id]: { choice: o.label } })} /> {o.label}. {o.text} </label>
                        ))}
                        {it.itemType === "NUMERIC" && <input type="number" onChange={(e) => setAnswers({ ...answers, [it.id]: { value: Number(e.target.value) } })} />}
                        <button onClick={() => show(`attempt ${it.id}`, (c) => c.POST("/v1/student/assignments/{assignment_id}/attempts", { params: { path: { assignment_id: work.id } }, body: { itemId: it.id, answer: answers[it.id] ?? {}, requestId: crypto.randomUUID() } }))}>Nộp câu này</button>
                      </div>
                    ))}
                  </>
                )}
              </>
            )}
          </div>
          <div className="col">
            <h2>Response thô</h2>
            {out ? (
              <>
                <p>
                  {out.label} → HTTP {out.status}
                  {out.mock && <span className="tag mock">MOCK (Prism)</span>}
                </p>
                <pre>{JSON.stringify(out.body, null, 2)}</pre>
              </>
            ) : <p>Chưa có request.</p>}
          </div>
        </div>
      </main>
    </>
  );
}
