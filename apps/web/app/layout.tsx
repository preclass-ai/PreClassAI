import type { Metadata, Viewport } from "next";
import { Be_Vietnam_Pro } from "next/font/google";
import type { ReactNode } from "react";
import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "PreClass AI", template: "%s · PreClass AI" },
  description: "Bài học có nguồn rõ ràng và lời giải do thầy cô duyệt.",
};

// Designed for Vietnamese: every diacritic comes from the same font (Avenir Next lacked them and mixed in fallbacks).
// next/font downloads it at build time and serves it from our own origin: no request to Google at runtime.
const sans = Be_Vietnam_Pro({
  subsets: ["vietnamese", "latin"],
  weight: ["400", "500", "600", "700", "800"],
  display: "swap",
  variable: "--font-sans",
});

export const viewport: Viewport = { width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="vi" className={sans.variable}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
