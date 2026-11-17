"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { StateBadge } from "@/components/badges";
import { Badge, DataNotice, Empty, ErrorBox, Loading, PageHeader } from "@/components/ui";
import { api, unwrap } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmtDateTime } from "@/lib/format";

export default function LessonsPage() {
  const { user } = useAuth();
  const lessons = useQuery({ queryKey: ["lessons"], queryFn: () => unwrap(api.GET("/v1/lessons")) });
  const isTeacher = user?.role === "TEACHER";

  return (
    <>
      <PageHeader
        title="Bài học"
        sub={isTeacher ? "Bài của bạn. Mỗi bài có các bản (revision); bản đã xuất bản không sửa được." : "Bài được giao cho bạn duyệt."}
        actions={
          isTeacher ? (
            <Link className="btn btn-primary" href="/lessons/new">
              Tạo bài mới
            </Link>
          ) : null
        }
      />
      <DataNotice />
      <ErrorBox error={lessons.error} />
      {lessons.isPending ? (
        <Loading />
      ) : lessons.data?.items.length === 0 ? (
        <Empty>Chưa có bài nào.</Empty>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Bài</th>
                <th>Lớp</th>
                <th>Bản hiện tại</th>
                <th>Tiến độ duyệt</th>
                <th>Ngày tạo</th>
              </tr>
            </thead>
            <tbody>
              {lessons.data?.items.map((l) => {
                const c = l.currentRevision.counts;
                return (
                  <tr key={l.id}>
                    <td>
                      <Link href={`/lessons/${l.id}`}>{l.title}</Link>
                      {l.currentRevision.newerSourceAvailable ? (
                        <>
                          {" "}
                          <Badge tone="warning">Có bản nguồn mới</Badge>
                        </>
                      ) : null}
                    </td>
                    <td>{l.grade}</td>
                    <td>
                      #{l.currentRevision.revisionNo} <StateBadge state={l.currentRevision.state} />
                    </td>
                    <td>
                      {c.total ? (
                        <>
                          {c.approved ?? 0}/{c.total} đã duyệt
                          {c.flagged ? <span className="text-danger"> · {c.flagged} có vấn đề</span> : null}
                          {c.reviewAgain ? <span className="text-warning"> · {c.reviewAgain} cần duyệt lại</span> : null}
                        </>
                      ) : (
                        <span className="muted">Chưa có nội dung</span>
                      )}
                    </td>
                    <td>{fmtDateTime(l.createdAt)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
