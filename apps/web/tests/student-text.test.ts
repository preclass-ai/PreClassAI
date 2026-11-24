import { describe, expect, it } from "vitest";
import { isTeacherOnly, studentText } from "@/lib/student-text";

describe("student text", () => {
  it("hides lesson-plan scaffolding and in-class prompts", () => {
    expect(isTeacherOnly("a) Mục tiêu:Vận dụng tri thức địa lí giải quyết vấn đề thực tiễn.")).toBe(true);
    expect(
      isTeacherOnly("* Câu hỏi: Lật các số và cho biết tên nghề nghiệp được thể hiện qua bức tranh, những nghề đó có liên quan gì tới kiến thức môn Địa lí?"),
    ).toBe(true);
    expect(isTeacherOnly("Bước 1: GV chuyển giao nhiệm vụ.")).toBe(true);
    expect(isTeacherOnly("Đọc bảng số liệu và trả lời các câu hỏi sau.")).toBe(false);
    expect(isTeacherOnly("Em hãy vẽ biểu đồ dân số của địa phương mình.")).toBe(false);
  });

  it("cites the lesson, not the plan", () => {
    expect(studentText("Theo giáo án, môn Địa lí giúp học sinh:")).toBe("Theo bài học, môn Địa lí giúp học sinh:");
    expect(studentText("Giáo án viết rõ.")).toBe("Bài học viết rõ.");
  });
});
