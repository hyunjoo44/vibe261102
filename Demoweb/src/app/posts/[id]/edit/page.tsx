import { notFound } from "next/navigation";

import { updatePostAction } from "@/app/actions";
import { PostForm } from "@/components/post-form";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getPost } from "@/lib/posts";

export default async function EditPostPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const post = await getPost(Number(id));
  if (!post) notFound();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl">글 수정</CardTitle>
      </CardHeader>
      <CardContent>
        <PostForm
          action={updatePostAction.bind(null, post.id)}
          defaults={post}
          cancelHref={`/posts/${post.id}`}
          submitLabel="수정 완료"
          isEdit
        />
      </CardContent>
    </Card>
  );
}
