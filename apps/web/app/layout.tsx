import type { Metadata, Viewport } from "next";
import { Be_Vietnam_Pro } from "next/font/google";
import type { ReactNode } from "react";
import { PWA_BOOT_SCRIPT } from "@/lib/pwa-boot";
import { THEME_BOOT_SCRIPT } from "@/lib/theme";
import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "PreClass AI · Học trước, hiểu sâu", template: "%s · PreClass AI" },
  description: "Học trước, hiểu sâu: bài học có nguồn rõ ràng và lời giải do thầy cô duyệt.",
  applicationName: "PreClass AI",
  // Icon when the app is installed (manifest.ts) or added to an iPhone home screen (apple-touch-icon).
  icons: {
    icon: [
      { url: "/icons/favicon-32.png", sizes: "32x32", type: "image/png" },
      { url: "/icons/favicon-48.png", sizes: "48x48", type: "image/png" },
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
    ],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180" }],
  },
  appleWebApp: { capable: true, title: "PreClass AI", statusBarStyle: "default" },
  formatDetection: { telephone: false },
};

// Designed for Vietnamese: every diacritic comes from the same font (Avenir Next lacked them and mixed in fallbacks).
// next/font downloads it at build time and serves it from our own origin: no request to Google at runtime.
const sans = Be_Vietnam_Pro({
  subsets: ["vietnamese", "latin"],
  weight: ["400", "500", "600", "700", "800"],
  display: "swap",
  variable: "--font-sans",
});

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  // Browser bar / installed-app title bar follow the page surface in each theme.
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f2f7f4" },
    { media: "(prefers-color-scheme: dark)", color: "#102229" },
  ],
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    // suppressHydrationWarning: the boot script sets data-theme on <html> before React hydrates.
    <html lang="vi" className={sans.variable} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOT_SCRIPT }} />
        <script dangerouslySetInnerHTML={{ __html: PWA_BOOT_SCRIPT }} />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
