"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, use } from "react";
import { StateBadge } from "@/components/badges";
import { NextStep } from "@/components/next-step";
import { ErrorBox, Loading, PageHeader } from "@/components/ui";
import { LessonAssignments } from "@/features/assignments";
import { Editor } from "@/features/editor";
import { History } from "@/features/history";
import { useLesson } from "@/features/lesson-data";
import { PublishGate } from "@/features/publish";
import { ReviewQueue } from "@/features/review";
import { isLocked } from "@/lib/blocks";
import { useAuth } from "@/lib/auth";

const TABS = [
  { id: "editor", label: "Soạn & nguồn", teacherOnly: false },
  { id: "review", label: "Duyệt", teacherOnly: false },
  { id: "publish", label: "Xuất bản & giao bài", teacherOnly: true },
  { id: "history", label: "Lịch sử", teacherOnly: false },
] as const;
type TabId = (typeof TABS)[number]["id"];

function LessonWorkspace({ lessonId }: { lessonId: string }) {
  const { user } = useAuth();
  const isTeacher = user?.role === "TEACHER";
  const router = useRouter();
  const params = useSearchParams();
  const tabs = TABS.filter((t) => isTeacher || !t.teacherOnly);
  const requested = params.get("tab");
  const tab: TabId = tabs.find((t) => t.id === requested)?.id ?? "editor";
  const lesson = useLesson(lessonId);

  if (lesson.isPending) return <Loading />;
  if (!lesson.data) return <ErrorBox error={lesson.error} />;
  const l = lesson.data;
  const rev = l.currentRevision;
  const c = rev.counts;

  return (
    <>
      <p className="crumbs">
        <Link href="/lessons">← Bài học</Link>
      </p>
      <PageHeader
        title={l.title}
        sub={
          <>
            Lớp {l.grade} · Bản #{rev.revisionNo} <StateBadge state={rev.state} /> · {c.approved ?? 0}/{c.total ?? 0} khối đã
            duyệt
            {c.flagged ? ` · ${c.flagged} có vấn đề` : ""}
            {c.reviewAgain ? ` · ${c.reviewAgain} cần duyệt lại` : ""}
            {l.goal ? <span className="block muted">Mục tiêu: {l.goal}</span> : null}
          </>
        }
      />
      {isTeacher ? <LessonAssignments lessonId={l.id} /> : null}
      <nav className="tabs" role="tablist" aria-label="Các bước của bài">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            className={tab === t.id ? "tab on" : "tab"}
            onClick={() => router.replace(`?tab=${t.id}`, { scroll: false })}
          >
            {t.label}
          </button>
        ))}
      </nav>
      <div role="tabpanel">
        {tab === "editor" ? <Editor lesson={l} canEdit={isTeacher} /> : null}
        {tab === "review" ? <ReviewQueue lesson={l} /> : null}
        {tab === "publish" && isTeacher ? <PublishGate lesson={l} /> : null}
        {tab === "history" ? <History lesson={l} canEdit={isTeacher} /> : null}
      </div>
      {tab === "editor" ? (
        <NextStep label="Tiếp: Duyệt" href="?tab=review" blockedBy={(c.total ?? 0) === 0 ? "Bài chưa có khối nào để duyệt." : null} />
      ) : null}
      {tab === "review" && isTeacher ? (
        <NextStep
          label="Tiếp: Xuất bản"
          href="?tab=publish"
          blockedBy={!isLocked(rev.state) && (c.approved ?? 0) < (c.total ?? 0) ? `Còn ${(c.total ?? 0) - (c.approved ?? 0)} khối chưa duyệt.` : null}
        />
      ) : null}
      {tab === "publish" && isTeacher ? (
        <NextStep label="Tiếp: Giao bài" href="#giao-bai" blockedBy={!isLocked(rev.state) ? "Hãy xuất bản bản này trước." : null} />
      ) : null}
    </>
  );
}

export default function LessonPage({ params }: { params: Promise<{ lessonId: string }> }) {
  const { lessonId } = use(params);
  return (
    <Suspense fallback={<Loading />}>
      <LessonWorkspace lessonId={lessonId} />
    </Suspense>
  );
}
