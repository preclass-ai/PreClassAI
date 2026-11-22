"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { use, useState } from "react";
import { Badge, Button, ErrorBox, Loading, PageHeader } from "@/components/ui";
import { AnchorTable } from "@/features/anchors";
import { NewRevisionForm } from "@/features/source-form";
import { api, unwrap } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmtDateTime } from "@/lib/format";
import { VISIBILITY } from "@/lib/labels";
import { refresh } from "@/lib/query";

export default function SourceDetailPage({ params }: { params: Promise<{ sourceId: string }> }) {
  const { sourceId } = use(params);
  const { user } = useAuth();
  const qc = useQueryClient();
  const [uploading, setUploading] = useState(false);
  const source = useQuery({
    queryKey: ["source", sourceId],
    queryFn: () => unwrap(api.GET("/v1/sources/{source_id}", { params: { path: { source_id: sourceId } } })),
  });
  const rev = source.data?.latestRevision;
  const anchors = useQuery({
    queryKey: ["anchors", rev?.id],
    enabled: !!rev,
    queryFn: () =>
      unwrap(
        api.GET("/v1/source-revisions/{source_revision_id}/anchors", {
          params: { path: { source_revision_id: rev!.id } },
        }),
      ),
  });

  if (source.isPending) return <Loading />;
  if (!source.data) return <ErrorBox error={source.error} />;
  const s = source.data;
  const isOwner = s.ownerId === user?.id;

  return (
    <>
      <p className="crumbs">
        <Link href="/sources">← Thư viện nguồn</Link>
      </p>
      <PageHeader
        title={s.title}
        sub={
          <>
            Bản #{rev?.version} · {rev?.anchorCount} đoạn · {VISIBILITY[s.visibility]} ·
            tải lên {fmtDateTime(rev?.createdAt)}
            {s.licenseNote ? ` · ${s.licenseNote}` : ""}
          </>
        }
        actions={
          isOwner ? (
            <Button onClick={() => setUploading((v) => !v)}>{uploading ? "Đóng" : "Tải bản mới"}</Button>
          ) : (
            <Badge>Chỉ xem</Badge>
          )
        }
      />
      {uploading ? (
        <section className="card">
          <h2>Bản nguồn mới</h2>
          <NewRevisionForm
            sourceId={s.id}
            onCreated={() => {
              setUploading(false);
              void refresh(qc, { queryKey: ["source", sourceId] });
              void refresh(qc, { queryKey: ["sources"] });
            }}
          />
        </section>
      ) : null}
      <section className="card">
        <h2>Đoạn nguồn (bản v{rev?.version})</h2>
        <ErrorBox error={anchors.error} />
        {anchors.isPending ? <Loading /> : <AnchorTable anchors={anchors.data?.items ?? []} />}
      </section>
    </>
  );
}
