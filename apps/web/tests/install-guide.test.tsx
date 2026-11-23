import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

const push = vi.fn();
vi.mock("next/navigation", () => ({ usePathname: () => "/sources", useRouter: () => ({ push }) }));

import manifest from "../app/manifest";
import { installSteps, InstallApp } from "@/features/install-app";
import { answerGuide, teacherTourSteps, tourFor } from "@/features/teacher-guide/faq";
import { TeacherCompanion } from "@/features/teacher-guide/companion";
import { detectDevice } from "@/lib/pwa";

beforeAll(() => {
  window.matchMedia = ((q: string) => ({ matches: false, media: q, addEventListener() {}, removeEventListener() {} })) as unknown as typeof window.matchMedia;
});
afterEach(() => {
  cleanup();
  localStorage.clear();
});

const IPHONE_26 = "Mozilla/5.0 (iPhone; CPU iPhone OS 26_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Mobile/15E148 Safari/604.1";
const IPHONE_ZALO = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Zalo iOS";
const SAMSUNG = "Mozilla/5.0 (Linux; Android 14; SM-A546E) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/25.0 Chrome/121.0 Mobile Safari/537.36";
const MAC_SAFARI = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15";

describe("install the app", () => {
  it("declares an installable manifest with the new icon", () => {
    const m = manifest();
    expect(m.display).toBe("standalone");
    expect(m.short_name).toBe("PreClass AI");
    expect(m.icons?.map((i) => `${i.sizes}:${i.purpose}`)).toEqual(expect.arrayContaining(["192x192:any", "512x512:any", "512x512:maskable"]));
  });

  it("recognizes phones, in-app browsers and Safari on a Mac", () => {
    expect(detectDevice(IPHONE_26)).toMatchObject({ ios: true, mobile: true, safari: 26, inApp: null });
    expect(detectDevice(IPHONE_ZALO).inApp).toBe("Zalo");
    expect(detectDevice(SAMSUNG)).toMatchObject({ android: true, samsung: true });
    expect(detectDevice("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)", "MacIntel", 5).ipad).toBe(true); // iPadOS
    expect(detectDevice(MAC_SAFARI).macSafari).toBe(true);
  });

  it("gives each phone its own wording", () => {
    expect(installSteps("ios", detectDevice(IPHONE_26))[0]?.sub).toMatch(/iOS 26/);
    expect(installSteps("ios", detectDevice(IPHONE_26))[1]?.title).toBe("Chọn “Thêm vào MH chính”");
    expect(installSteps("android", detectDevice(SAMSUNG))[1]?.title).toMatch(/Màn hình chờ/);
    expect(installSteps("desktop", detectDevice(MAC_SAFARI))[1]?.title).toBe("Chọn “Thêm vào Dock”");
  });

  it("shows the steps, switches tabs, and has no one-tap button when the browser offers none", () => {
    render(<InstallApp audience="teacher" />);
    expect(screen.getByRole("heading", { name: /Cài PreClass AI/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Cài ngay/ })).toBeNull();
    fireEvent.click(screen.getByRole("tab", { name: /Android/ }));
    expect(screen.getByText("Bấm nút ⋮ ở góc trên bên phải")).toBeInTheDocument();
  });

  it("offers one tap when Chrome kept an install event", async () => {
    const prompt = vi.fn(async () => {});
    (window as unknown as { __pcInstall: unknown }).__pcInstall = Object.assign(new Event("beforeinstallprompt"), { prompt, userChoice: Promise.resolve({ outcome: "accepted" }) });
    render(<InstallApp audience="student" />);
    fireEvent.click(screen.getByRole("button", { name: /Cài ngay trên máy này/ }));
    await screen.findByText(/Đang cài/);
    expect(prompt).toHaveBeenCalledOnce();
    expect(screen.queryByRole("button", { name: /Cài ngay/ })).toBeNull(); // the event is used once
  });
});

describe("Bé Cầu, the teachers' guide", () => {
  it("answers how-to questions by keyword", () => {
    expect(answerGuide("Làm sao nhắc học sinh chưa làm bài?").text).toMatch(/Sao chép lời nhắc/);
    expect(answerGuide("tải kết quả ra excel").text).toMatch(/CSV/);
    expect(answerGuide("giao bài cho lớp thế nào").actions?.[0]).toMatchObject({ kind: "go", href: "/classes" });
    expect(answerGuide("bắt đầu từ đâu").text).toMatch(/Ba bước/);
    expect(answerGuide("thời tiết hôm nay").follow?.length).toBeGreaterThan(0); // unknown: offers topics
  });

  it("has a tour for the dashboard and the classes page", () => {
    expect(tourFor("/lessons")).toBe("lessons");
    expect(tourFor("/lessons/abc")).toBe("page");
    expect(teacherTourSteps("lessons").map((s) => s.target)).toEqual(expect.arrayContaining(["progress", "new-lesson", "teacher-guide"]));
  });

  it("opens from the floating globe and moves to a page from an answer", () => {
    render(<TeacherCompanion />);
    fireEvent.click(screen.getByRole("button", { name: "Hỏi Bé Cầu: hướng dẫn sử dụng" }));
    expect(screen.getByRole("dialog", { name: "Hỏi Bé Cầu cách dùng" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Bắt đầu từ đâu?" }));
    fireEvent.click(screen.getByRole("button", { name: "Mở trang Nguồn" }));
    expect(push).toHaveBeenCalledWith("/sources");
  });
});
