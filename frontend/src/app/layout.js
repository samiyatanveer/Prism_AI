import { Inter } from "next/font/google";
import "./globals.css";
import Providers from "@/providers/providers";
import { Toaster } from "sonner";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
  display: "swap",
});

export const metadata = {
  title: {
    default: "PrismAI — Crypto Intelligence",
    template: "%s | PrismAI",
  },
  description:
    "AI-powered crypto trading intelligence. Connect your exchange, ask questions in plain language, and get data-driven analysis.",
  keywords: ["crypto", "AI", "trading", "portfolio", "Bitcoin", "analysis"],
  robots: { index: false }, // Private platform — no public indexing
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased dark`}>
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <Providers>{children}</Providers>
        {/*
          Sonner toast container.
          Theme is set to "dark" to match the app default.
          Future features use: import { toast } from "sonner"
          then call toast.success(), toast.error(), toast.info() etc.
        */}
        <Toaster theme="dark" position="bottom-right" richColors closeButton />
      </body>
    </html>
  );
}
