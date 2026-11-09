import type { Metadata, Viewport } from "next";
import { Host_Grotesk, Instrument_Sans } from "next/font/google";
import "./globals.css";

const hostGrotesk = Host_Grotesk({ subsets: ["latin"], variable: "--font-host-grotesk", display: "swap" });
const instrumentSans = Instrument_Sans({ subsets: ["latin"], variable: "--font-instrument-sans", display: "swap" });

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
  themeColor: "#fcfcfd",
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
    <html lang="en" className={`h-full ${hostGrotesk.variable} ${instrumentSans.variable}`}>
      <body className="h-full flex flex-col bg-ground text-ink antialiased selection:bg-ink selection:text-ground">
        {/* Main application container with mobile safe-area paddings */}
        <div className="flex-1 flex flex-col w-full max-w-md mx-auto sm:max-w-xl md:max-w-4xl lg:max-w-6xl pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)]">
          {children}
        </div>
      </body>
    </html>
  );
}
