import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, Eye, Pencil } from "lucide-react";

import { addCommentAction, deleteCommentAction, deletePostAction } from "@/app/actions";
import { DeleteButton } from "@/components/delete-button";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { formatDate } from "@/lib/format";
import { getPost, incrementViews } from "@/lib/posts";

export const dynamic = "force-dynamic";

export default async function PostPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const postId = Number(id);
  await incrementViews(postId);
  const post = await getPost(postId);
  if (!post) notFound();

  const edited = post.updatedAt !== post.createdAt;

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader className="gap-3">
          <div>
            <Badge variant={post.category === "공지" ? "default" : "secondary"}>{post.category}</Badge>
          </div>
          <CardTitle className="text-2xl leading-snug">{post.title}</CardTitle>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
            <span className="font-medium text-foreground">{post.author}</span>
            <span>{formatDate(post.createdAt, true)}</span>
            {edited && <span>(수정됨 {formatDate(post.updatedAt, true)})</span>}
            <span className="flex items-center gap-1">
              <Eye className="size-3.5" />
              {post.views}
            </span>
          </div>
        </CardHeader>
        <Separator />
        <CardContent className="min-h-48 whitespace-pre-wrap py-6 leading-relaxed">
          {post.content}
        </CardContent>
        <CardFooter className="justify-between">
          <Link href="/" className={buttonVariants({ variant: "outline" })}>
            <ArrowLeft />
            목록
          </Link>
          <div className="flex gap-2">
            <Link href={`/posts/${post.id}/edit`} className={buttonVariants({ variant: "secondary" })}>
              <Pencil />
              수정
            </Link>
            <DeleteButton
              onDelete={deletePostAction.bind(null, post.id)}
              confirmMessage="이 게시글을 삭제하시겠습니까?"
              label="삭제"
            />
          </div>
        </CardFooter>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>댓글 {post.comments.length}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {post.comments.length === 0 ? (
            <p className="text-sm text-muted-foreground">첫 댓글을 남겨보세요.</p>
          ) : (
            <ul className="flex flex-col divide-y">
              {post.comments.map((comment) => (
                <li key={comment.id} className="flex items-start justify-between gap-4 py-3">
                  <div className="flex min-w-0 flex-col gap-1">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="font-medium">{comment.author}</span>
                      <span className="text-muted-foreground">{formatDate(comment.createdAt, true)}</span>
                    </div>
                    <p className="whitespace-pre-wrap break-words text-sm">{comment.content}</p>
                  </div>
                  <DeleteButton
                    onDelete={deleteCommentAction.bind(null, post.id, comment.id)}
                    confirmMessage="이 댓글을 삭제하시겠습니까?"
                  />
                </li>
              ))}
            </ul>
          )}

          <Separator />

          <form action={addCommentAction.bind(null, post.id)} className="flex flex-col gap-2">
            <Input name="author" placeholder="작성자" required className="sm:w-48" />
            <Textarea name="content" placeholder="댓글을 입력하세요" required className="min-h-20" />
            <div className="flex justify-end">
              <Button type="submit">댓글 등록</Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
