import type { Metadata } from "next";
import Link from "next/link";
import { Geist } from "next/font/google";
import { Snowflake, TreePine } from "lucide-react";

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
      <body className="christmas-bg min-h-screen antialiased">
        <div className="snow" aria-hidden />
        <div className="christmas-ground" aria-hidden />
        <header className="relative z-10 bg-red-800 text-white shadow-lg">
          <div className="mx-auto flex h-14 max-w-4xl items-center justify-between px-4">
            <Link href="/" className="flex items-center gap-2 font-semibold">
              <TreePine className="size-5 text-green-300" />
              Demoweb 게시판
              <Snowflake className="size-4 text-sky-200" />
            </Link>
            <Link
              href="/posts/new"
              className={buttonVariants({ size: "sm", className: "bg-white text-red-800 hover:bg-white/90" })}
            >
              글쓰기
            </Link>
          </div>
          <div className="christmas-lights" />
        </header>
        <main className="relative z-10 mx-auto max-w-4xl px-4 pt-8 pb-48">{children}</main>
      </body>
    </html>
  );
}
