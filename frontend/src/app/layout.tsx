import type { Metadata, Viewport } from "next";
import "./globals.css";

/**
 * Viewport configuration optimized for mobile browsers.
 * Disables unexpected browser pinch-zoom while logging on gym floors
 * and ensures full viewport coverage under iPhone notches and status bars.
 */
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: "cover",
  themeColor: "#0f172a",
};

export const metadata: Metadata = {
  title: "Trainer Progression App",
  description: "Mobile-first workout progression and client logging assistant for personal trainers.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full flex flex-col bg-slate-900 text-slate-100 antialiased selection:bg-emerald-500 selection:text-white">
        {/* Main application container with mobile safe-area paddings */}
        <div className="flex-1 flex flex-col w-full max-w-md mx-auto sm:max-w-xl md:max-w-4xl lg:max-w-6xl pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)]">
          {children}
        </div>
      </body>
    </html>
  );
}
