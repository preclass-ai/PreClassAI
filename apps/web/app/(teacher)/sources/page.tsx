"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { Badge, Button, Empty, ErrorBox, Loading, PageHeader } from "@/components/ui";
import { NewSourceForm } from "@/features/source-form";
import { api, unwrap } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { VISIBILITY } from "@/lib/labels";
import { fmtDateTime } from "@/lib/format";
import { refresh } from "@/lib/query";

export default function SourcesPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [adding, setAdding] = useState(false);
  const sources = useQuery({ queryKey: ["sources"], queryFn: () => unwrap(api.GET("/v1/sources")) });

  return (
    <>
      <PageHeader
        title="Thư viện nguồn"
        sub="Tài liệu gốc (sách giáo khoa, bảng số liệu…) để AI soạn bài và để thầy cô đối chiếu khi duyệt."
        actions={
          <Button variant="primary" onClick={() => setAdding((v) => !v)}>
            {adding ? "Đóng" : "Thêm nguồn"}
          </Button>
        }
      />
      {adding ? (
        <section className="card">
          <h2>Nguồn mới</h2>
          <NewSourceForm
            onSaved={() => void refresh(qc, { queryKey: ["sources"] })}
            onCreated={() => {
              setAdding(false);
              void refresh(qc, { queryKey: ["sources"] });
            }}
          />
        </section>
      ) : null}
      <ErrorBox error={sources.error} />
      {sources.isPending ? (
        <Loading />
      ) : sources.data?.items.length === 0 ? (
        <Empty>Chưa có nguồn. Bấm &quot;Thêm nguồn&quot; để dán văn bản hoặc tải tệp Word, PDF, Excel, PowerPoint.</Empty>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Tên nguồn</th>
                <th>Ai dùng được</th>
                <th>Phiên bản</th>
                <th>Số đoạn</th>
                <th>Đọc tệp</th>
                <th>Ngày tạo</th>
              </tr>
            </thead>
            <tbody>
              {sources.data?.items.map((s) => (
                <tr key={s.id}>
                  <td>
                    <Link href={`/sources/${s.id}`}>{s.title}</Link>
                    {s.ownerId !== user?.id ? <span className="muted small"> · của đồng nghiệp</span> : null}
                  </td>
                  <td>{VISIBILITY[s.visibility]}</td>
                  <td>Bản #{s.latestRevision.version}</td>
                  <td>{s.latestRevision.anchorCount}</td>
                  <td>
                    <Badge tone={s.latestRevision.extractStatus === "OK" ? "success" : s.latestRevision.extractStatus === "FAILED" ? "danger" : "info"}>
                      {s.latestRevision.extractStatus === "OK" ? "Đã đọc" : s.latestRevision.extractStatus === "FAILED" ? "Lỗi" : "Đang đọc"}
                    </Badge>
                  </td>
                  <td>{fmtDateTime(s.createdAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
