"use client";

import { useEffect, useState, type ReactNode } from "react";
import { promptInstall, useDevice, useInstallPrompt, useJustInstalled, useStandalone, type Device } from "@/lib/pwa";

/**
 * "Cài PreClass AI": one block at the bottom of the teacher and student dashboards.
 * - Chrome/Edge/Samsung give a one-tap button (the system dialog asks to confirm).
 * - iPhone/iPad never do, so the block shows the three Share-sheet steps; Android and computers have their own tab.
 * - Inside Zalo/Facebook nothing can be installed: say so first and offer to copy the link.
 * - Already opened from the home screen: one line, nothing to do.
 * A small reminder slides up on phones after a few seconds; "×" hides it for 7 days.
 */
type Audience = "student" | "teacher";
type Tab = "ios" | "android" | "desktop";

const SNOOZE_KEY = "preclass.install.snooze";
export const INSTALL_ANCHOR = "cai-app";

const Svg = {
  share: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3v12" /><path d="M8 7l4-4 4 4" /><path d="M6 11H5a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-8a1 1 0 0 0-1-1h-1" />
    </svg>
  ),
  add: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" aria-hidden="true">
      <rect x="3.5" y="3.5" width="17" height="17" rx="4" /><path d="M12 8v8M8 12h8" />
    </svg>
  ),
  dots: (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="5" cy="12" r="2" /><circle cx="12" cy="12" r="2" /><circle cx="19" cy="12" r="2" /></svg>
  ),
  vdots: (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="12" cy="5" r="2" /><circle cx="12" cy="12" r="2" /><circle cx="12" cy="19" r="2" /></svg>
  ),
  download: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 4v11" /><path d="M7 10l5 5 5-5" /><path d="M5 20h14" />
    </svg>
  ),
  monitorDown: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="4" width="18" height="12" rx="2" /><path d="M8 20h8M12 16v4" /><path d="M12 7v5M9.5 9.5 12 12l2.5-2.5" />
    </svg>
  ),
  apple: (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M16.4 12.6c0-2.3 1.9-3.4 2-3.5-1.1-1.6-2.8-1.8-3.4-1.8-1.4-.1-2.8.9-3.5.9-.7 0-1.8-.8-3-.8-1.5 0-3 .9-3.8 2.3-1.6 2.8-.4 7 1.2 9.3.8 1.1 1.7 2.4 2.9 2.3 1.2 0 1.6-.7 3-.7s1.8.7 3 .7c1.3 0 2.1-1.1 2.8-2.3.9-1.3 1.3-2.6 1.3-2.6s-2.5-1-2.5-3.8zM14.1 5.8c.6-.8 1.1-1.8 1-2.9-.9 0-2.1.6-2.7 1.4-.6.7-1.1 1.8-1 2.8 1 .1 2.1-.5 2.7-1.3z" />
    </svg>
  ),
  android: (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M17.6 9.5l1.6-2.8a.4.4 0 0 0-.7-.4l-1.7 2.9A10 10 0 0 0 12 8.3c-1.7 0-3.3.3-4.8.9L5.5 6.3a.4.4 0 0 0-.7.4l1.6 2.8A9 9 0 0 0 2 16.6h20a9 9 0 0 0-4.4-7.1zM7.3 14a1 1 0 1 1 0-2 1 1 0 0 1 0 2zm9.4 0a1 1 0 1 1 0-2 1 1 0 0 1 0 2z" />
    </svg>
  ),
  laptop: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="4" y="5" width="16" height="11" rx="1.5" /><path d="M2 19h20" />
    </svg>
  ),
};

interface Step { title: string; sub?: string; mock?: ReactNode }

/** Pure so tests can check each phone's wording. */
export function installSteps(tab: Tab, d: Device | null): Step[] {
  const iconLine = "Biểu tượng PreClass AI xuất hiện ở màn hình chính. Mở từ đó là chạy toàn màn hình như ứng dụng.";
  if (tab === "ios") {
    const v26 = !d?.ios || d.safari >= 26;
    const first: Step = d?.iosOther
      ? { title: "Bấm nút Chia sẻ trên thanh địa chỉ", sub: "Chrome, Edge trên iPhone cũng có nút này. Không thấy thì mở trang bằng Safari.", mock: <>{Svg.share} Chia sẻ</> }
      : d?.ipad
        ? { title: "Bấm nút Chia sẻ ở góc trên bên phải", sub: "Hình vuông có mũi tên đi lên.", mock: <>{Svg.share} Chia sẻ</> }
        : {
            title: "Bấm nút Chia sẻ trong Safari",
            sub: v26 ? "iOS 26: bấm nút ⋯ ở góc dưới bên phải trước, rồi chọn Chia sẻ." : "Hình vuông có mũi tên đi lên, ở thanh dưới cùng.",
            mock: v26 ? <>{Svg.dots} → {Svg.share} Chia sẻ</> : <>{Svg.share} Chia sẻ</>,
          };
    return [
      first,
      { title: "Chọn “Thêm vào MH chính”", sub: "Kéo xuống trong danh sách. Chưa thấy thì bấm “Sửa tác vụ” để bật.", mock: <>{Svg.add} Thêm vào MH chính</> },
      { title: "Bấm “Thêm”", sub: iconLine },
    ];
  }
  if (tab === "android") {
    return d?.samsung
      ? [
          { title: "Bấm nút ≡ ở thanh dưới cùng", sub: "Trình duyệt Samsung Internet.", mock: <>≡ Menu</> },
          { title: "Chọn “Thêm trang vào” › “Màn hình chờ”", mock: <>{Svg.add} Màn hình chờ</> },
          { title: "Bấm “Thêm”", sub: iconLine },
        ]
      : [
          { title: "Bấm nút ⋮ ở góc trên bên phải", sub: "Trong Chrome. Trình duyệt khác thường có nút menu tương tự.", mock: Svg.vdots },
          { title: "Chọn “Cài đặt ứng dụng”", sub: "Máy cũ có thể ghi “Thêm vào màn hình chính”.", mock: <>{Svg.add} Cài đặt ứng dụng</> },
          { title: "Bấm “Cài đặt”", sub: iconLine },
        ];
  }
  if (d?.macSafari) {
    return [
      { title: "Mở menu Tệp của Safari", sub: "macOS Sonoma trở lên." },
      { title: "Chọn “Thêm vào Dock”", mock: <>{Svg.add} Thêm vào Dock</> },
      { title: "Bấm “Thêm”", sub: "PreClass AI nằm ở Dock, mở trong cửa sổ riêng như ứng dụng." },
    ];
  }
  return [
    { title: "Mở trang bằng Chrome hoặc Edge", sub: "Trên Mac dùng Safari thì vào menu Tệp › Thêm vào Dock." },
    { title: "Bấm biểu tượng cài đặt ở cuối thanh địa chỉ", sub: "Hoặc menu ⋮ › Truyền, lưu và chia sẻ › Cài đặt trang dưới dạng ứng dụng.", mock: <>{Svg.monitorDown} Cài đặt</> },
    { title: "Bấm “Cài đặt”", sub: "PreClass AI mở trong cửa sổ riêng, có biểu tượng trên thanh tác vụ hoặc Dock." },
  ];
}

function defaultTab(d: Device | null): Tab {
  if (d?.ios) return "ios";
  if (d?.android) return "android";
  return "desktop";
}

export function InstallApp({ audience }: { audience: Audience }) {
  const device = useDevice();
  const evt = useInstallPrompt();
  const standalone = useStandalone();
  const installed = useJustInstalled();
  const [tab, setTab] = useState<Tab | null>(null);
  const [note, setNote] = useState("");
  const you = audience === "student" ? "em" : "thầy cô";
  const current = tab ?? defaultTab(device);

  async function install() {
    const r = await promptInstall();
    if (r === "dismissed") setNote(`Chưa cài. Khi nào cần, ${you} quay lại đây bấm cài là được.`);
    if (r === "accepted") setNote("Đang cài… Biểu tượng PreClass AI sẽ có ở màn hình chính.");
  }

  async function copyLink() {
    const url = `${window.location.origin}/login`;
    try {
      await navigator.clipboard.writeText(url);
      setNote("Đã sao chép đường dẫn. Mở Safari hoặc Chrome rồi dán vào thanh địa chỉ.");
    } catch {
      setNote(`Đường dẫn: ${url}`);
    }
  }

  const title = audience === "student" ? "Cài PreClass AI lên điện thoại" : "Cài PreClass AI lên điện thoại và máy tính";

  return (
    <section className="install-app" id={INSTALL_ANCHOR} aria-labelledby="install-title" data-tour="install">
      <h2 id="install-title">{title}</h2>
      {standalone ? (
        <p className="install-ok">✓ {audience === "student" ? "Em" : "Thầy cô"} đang dùng PreClass AI như ứng dụng đã cài.</p>
      ) : (
        <>
          <div className="install-head">
            {/* eslint-disable-next-line @next/next/no-img-element -- static icon from /public, no optimisation needed */}
            <img src="/icons/icon-192.png" width={64} height={64} alt="Biểu tượng PreClass AI" />
            <div>
              <strong>PreClass AI</strong>
              <span>
                Thành biểu tượng ở màn hình chính, mở một chạm, toàn màn hình như ứng dụng. Miễn phí, không cần kho ứng dụng,
                {audience === "student" ? " không tốn bộ nhớ máy." : " cập nhật cùng bản web."}
              </span>
            </div>
          </div>
          {device?.inApp ? (
            <div className="install-warn" role="note">
              <strong>Trang đang mở trong {device.inApp}, nơi không cài được.</strong> Bấm nút {device.ios ? "⋯" : "⋮"} ở góc trên,
              chọn “Mở bằng trình duyệt”, rồi làm theo các bước dưới đây.
              <div>
                <button type="button" className="btn" onClick={() => void copyLink()}>Sao chép đường dẫn</button>
              </div>
            </div>
          ) : null}
          {installed ? <p className="install-ok">✓ Đã cài. Mở PreClass AI từ màn hình chính nhé.</p> : null}
          {evt ? (
            <div className="install-now">
              <button type="button" className="install-go" onClick={() => void install()}>
                {Svg.download} Cài ngay trên máy này
              </button>
              <span className="muted small">Một chạm, hệ điều hành sẽ hỏi xác nhận.</span>
            </div>
          ) : null}
          <div className="install-tabs" role="tablist" aria-label="Chọn loại máy">
            {([
              ["ios", Svg.apple, "iPhone, iPad"],
              ["android", Svg.android, "Android"],
              ["desktop", Svg.laptop, "Máy tính"],
            ] as const).map(([id, icon, label]) => (
              <button key={id} type="button" role="tab" aria-selected={current === id} onClick={() => setTab(id)}>
                {icon} {label}
              </button>
            ))}
          </div>
          <ol className="install-steps" role="tabpanel">
            {installSteps(current, device).map((s, i) => (
              <li key={s.title}>
                <span className="install-n" aria-hidden="true">{i + 1}</span>
                <div>
                  <b>{s.title}</b>
                  {s.sub ? <small>{s.sub}</small> : null}
                  {s.mock ? <span className="install-mock">{s.mock}</span> : null}
                </div>
              </li>
            ))}
          </ol>
          <p className="muted small" aria-live="polite">{note}</p>
        </>
      )}
      <InstallNudge audience={audience} />
    </section>
  );
}

/** Phones only, not installed, not snoozed: a small card slides up after 5 s. */
function InstallNudge({ audience }: { audience: Audience }) {
  const device = useDevice();
  const evt = useInstallPrompt();
  const standalone = useStandalone();
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (!device?.mobile || standalone) return;
    let snoozed = false;
    try {
      snoozed = Date.now() < Number(localStorage.getItem(SNOOZE_KEY) || 0);
    } catch {
      /* storage blocked: show it */
    }
    if (snoozed) return;
    const t = window.setTimeout(() => setShow(true), 5000);
    return () => window.clearTimeout(t);
  }, [device, standalone]);

  if (!show || standalone) return null;

  function later() {
    try {
      localStorage.setItem(SNOOZE_KEY, String(Date.now() + 7 * 86_400_000));
    } catch {
      /* blocked: it comes back next visit */
    }
    setShow(false);
  }

  async function go() {
    setShow(false);
    if (evt && (await promptInstall()) !== "unavailable") return;
    document.getElementById(INSTALL_ANCHOR)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div className="install-nudge" role="dialog" aria-label="Gợi ý cài ứng dụng">
      {/* eslint-disable-next-line @next/next/no-img-element -- static icon */}
      <img src="/icons/icon-192.png" width={42} height={42} alt="" />
      <div>
        <b>Cài PreClass AI lên màn hình chính</b>
        <span>{audience === "student" ? "Mở bài một chạm, toàn màn hình" : "Theo dõi lớp một chạm, toàn màn hình"}</span>
      </div>
      <button type="button" className="install-nudge-go" onClick={() => void go()}>{evt ? "Cài" : "Xem cách"}</button>
      <button type="button" className="install-nudge-no" onClick={later} aria-label="Để sau">×</button>
    </div>
  );
}
