"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef } from "react";
import { Badge, Button, Empty, ErrorBox, Loading, Notice, PageHeader } from "@/components/ui";
import { api, postForm, unwrap, type Schemas } from "@/lib/api";
import { fmtDate } from "@/lib/format";

export default function PlansPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const file = useRef<HTMLInputElement>(null);
  const list = useQuery({ queryKey: ["plans"], queryFn: () => unwrap(api.GET("/v1/lesson-plans")) });
  const upload = useMutation({
    mutationFn: (f: File) => {
      const form = new FormData();
      form.append("file", f);
      return postForm<{ items: Schemas["PlanOut"][] }>("/v1/lesson-plans", form);
    },
    onSuccess: async (res) => {
      await qc.invalidateQueries({ queryKey: ["plans"] });
      if (res.items.length === 1) router.push(`/plans/${res.items[0]!.id}`);
    },
  });

  return (
    <div className="stack">
      <PageHeader title="Giáo án" sub="Nạp giáo án (DOCX hoặc PDF có chữ). Hệ thống đọc ra mục tiêu, 4 hoạt động và câu trắc nghiệm để thầy cô kiểm tra rồi tạo bài chuẩn bị trước giờ học." />
      <section className="card stack">
        <label htmlFor="plan-file">Chọn tệp giáo án</label>
        <input id="plan-file" ref={file} type="file" accept=".docx,.pdf" />
        <Button
          variant="primary"
          busy={upload.isPending}
          onClick={() => {
            const f = file.current?.files?.[0];
            if (f) upload.mutate(f);
          }}
        >
          Đọc giáo án
        </Button>
        {upload.isPending ? <Notice>Đang đọc giáo án, tệp dài có thể mất khoảng một phút.</Notice> : null}
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
            </li>
          ))}
        </ul>
      ) : (
        <Empty>Chưa có giáo án nào.</Empty>
      )}
    </div>
  );
}
