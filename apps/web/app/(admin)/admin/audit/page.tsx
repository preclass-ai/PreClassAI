"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Empty, ErrorBox, Field, Loading, PageHeader } from "@/components/ui";
import { api, unwrap } from "@/lib/api";
import { fmtDateTime } from "@/lib/format";

export default function AuditPage() {
  const [action, setAction] = useState("");
  const logs = useQuery({
    queryKey: ["audit", action],
    queryFn: () =>
      unwrap(api.GET("/v1/admin/audit-logs", { params: { query: { action: action || undefined, limit: 200 } } })),
  });

  return (
    <>
      <PageHeader title="Nhật ký hệ thống" sub="Chỉ đọc. Không chứa nội dung bài làm hay lý do thu hồi." />
      <Field label="Lọc theo hành động">
        <input value={action} onChange={(e) => setAction(e.target.value.toUpperCase())} placeholder="vd: LOGIN, PUBLISH" />
      </Field>
      <ErrorBox error={logs.error} />
      {logs.isPending ? (
        <Loading />
      ) : logs.data?.items.length === 0 ? (
        <Empty>Không có bản ghi.</Empty>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Thời điểm</th>
                <th>Hành động</th>
                <th>Đối tượng</th>
                <th>Người thực hiện</th>
              </tr>
            </thead>
            <tbody>
              {logs.data?.items.map((l) => (
                <tr key={l.id}>
                  <td>{fmtDateTime(l.createdAt)}</td>
                  <td className="mono">{l.action}</td>
                  <td>
                    {l.resourceType}
                    {l.resourceId ? <span className="muted small mono"> {l.resourceId.slice(0, 8)}</span> : null}
                  </td>
                  <td className="mono small">{l.actorId?.slice(0, 8) ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
