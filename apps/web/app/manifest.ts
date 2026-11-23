import type { MetadataRoute } from "next";

/** Web app manifest: what the phone uses when PreClass AI is added to the home screen (src/features/install-app.tsx). */
export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "PreClass AI · Học trước, hiểu sâu",
    short_name: "PreClass AI",
    description: "Học trước, hiểu sâu: bài học có nguồn rõ ràng và lời giải do thầy cô duyệt.",
    lang: "vi",
    dir: "ltr",
    start_url: "/",
    scope: "/",
    display: "standalone",
    orientation: "any",
    background_color: "#f2f7f4",
    theme_color: "#0b6c80",
    categories: ["education"],
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/icon-maskable-192.png", sizes: "192x192", type: "image/png", purpose: "maskable" },
      { src: "/icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
