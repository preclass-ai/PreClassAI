"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { Badge, Button, DataNotice, Empty, ErrorBox, Loading, PageHeader } from "@/components/ui";
import { NewSourceForm } from "@/features/source-form";
import { api, unwrap } from "@/lib/api";
import { useAuth } from "@/lib/auth";
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
        sub="Nguồn là căn cứ để AI soạn và để giáo viên kiểm chứng. Bản nguồn đã tải lên không bị sửa."
        actions={
          <Button variant="primary" onClick={() => setAdding((v) => !v)}>
            {adding ? "Đóng" : "Thêm nguồn"}
          </Button>
        }
      />
      <DataNotice />
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
                <th>Phạm vi</th>
                <th>Bản</th>
                <th>Đoạn nguồn</th>
                <th>Trạng thái đọc</th>
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
                  <td>{s.visibility === "SCHOOL" ? "Cả trường" : "Riêng"}</td>
                  <td>v{s.latestRevision.version}</td>
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
