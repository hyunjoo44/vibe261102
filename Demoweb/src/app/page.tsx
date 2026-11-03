import Link from "next/link";
import { MessageCircle, Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDate } from "@/lib/format";
import { CATEGORIES, listPosts } from "@/lib/posts";
import { cn } from "@/lib/utils";

export const dynamic = "force-dynamic";

type SearchParams = Promise<{ q?: string; category?: string; page?: string }>;

function buildHref(params: { q?: string; category?: string; page?: number }) {
  const sp = new URLSearchParams();
  if (params.q) sp.set("q", params.q);
  if (params.category) sp.set("category", params.category);
  if (params.page && params.page > 1) sp.set("page", String(params.page));
  const qs = sp.toString();
  return qs ? `/?${qs}` : "/";
}

export default async function Home({ searchParams }: { searchParams: SearchParams }) {
  const { q = "", category = "", page = "1" } = await searchParams;
  const result = await listPosts({ query: q, category, page: Number(page) || 1 });

  return (
    <Card>
      <CardHeader className="gap-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-xl">전체 게시글</CardTitle>
          <span className="text-sm text-muted-foreground">총 {result.total}개</span>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <nav className="flex flex-wrap gap-1">
            {["", ...CATEGORIES].map((c) => (
              <Link
                key={c || "all"}
                href={buildHref({ q, category: c })}
                className={buttonVariants({
                  size: "sm",
                  variant: category === c ? "default" : "ghost",
                })}
              >
                {c || "전체"}
              </Link>
            ))}
          </nav>

          <form action="/" className="flex gap-2">
            {category && <input type="hidden" name="category" value={category} />}
            <Input name="q" defaultValue={q} placeholder="제목, 내용, 작성자 검색" className="w-full sm:w-56" />
            <Button type="submit" variant="outline" size="icon" aria-label="검색">
              <Search />
            </Button>
          </form>
        </div>
      </CardHeader>

      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-16 text-center">번호</TableHead>
              <TableHead>제목</TableHead>
              <TableHead className="hidden w-28 sm:table-cell">작성자</TableHead>
              <TableHead className="hidden w-28 sm:table-cell">작성일</TableHead>
              <TableHead className="w-16 text-center">조회</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {result.posts.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="h-32 text-center text-muted-foreground">
                  {q ? `"${q}"에 대한 검색 결과가 없습니다.` : "게시글이 없습니다. 첫 글을 작성해 보세요!"}
                </TableCell>
              </TableRow>
            ) : (
              result.posts.map((post) => (
                <TableRow key={post.id} className={cn(post.category === "공지" && "bg-muted/50")}>
                  <TableCell className="text-center text-muted-foreground">{post.id}</TableCell>
                  <TableCell>
                    <Link href={`/posts/${post.id}`} className="flex min-w-0 items-center gap-2 hover:underline">
                      <Badge variant={post.category === "공지" ? "default" : "secondary"}>
                        {post.category}
                      </Badge>
                      <span className="truncate font-medium">{post.title}</span>
                      {post.commentCount > 0 && (
                        <span className="flex shrink-0 items-center gap-0.5 text-xs text-muted-foreground">
                          <MessageCircle className="size-3" />
                          {post.commentCount}
                        </span>
                      )}
                    </Link>
                  </TableCell>
                  <TableCell className="hidden sm:table-cell">{post.author}</TableCell>
                  <TableCell className="hidden text-muted-foreground sm:table-cell">
                    {formatDate(post.createdAt)}
                  </TableCell>
                  <TableCell className="text-center text-muted-foreground">{post.views}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>

        {result.totalPages > 1 && (
          <nav className="mt-6 flex justify-center gap-1">
            {Array.from({ length: result.totalPages }, (_, i) => i + 1).map((p) => (
              <Link
                key={p}
                href={buildHref({ q, category, page: p })}
                className={buttonVariants({
                  size: "icon-sm",
                  variant: p === result.page ? "default" : "outline",
                })}
              >
                {p}
              </Link>
            ))}
          </nav>
        )}
      </CardContent>
    </Card>
  );
}
