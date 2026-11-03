import type { Metadata } from "next";
import Link from "next/link";
import { Geist } from "next/font/google";
import { MessageSquareText } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import "./globals.css";

const geist = Geist({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: "Demoweb 게시판",
  description: "Next.js + shadcn/ui + TypeScript 게시판",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" className={cn("font-sans", geist.variable)}>
      <body className="min-h-screen bg-muted/30 antialiased">
        <header className="border-b bg-background">
          <div className="mx-auto flex h-14 max-w-4xl items-center justify-between px-4">
            <Link href="/" className="flex items-center gap-2 font-semibold">
              <MessageSquareText className="size-5" />
              Demoweb 게시판
            </Link>
            <Link href="/posts/new" className={buttonVariants({ size: "sm" })}>
              글쓰기
            </Link>
          </div>
        </header>
        <main className="mx-auto max-w-4xl px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
