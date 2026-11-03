import { createPostAction } from "@/app/actions";
import { PostForm } from "@/components/post-form";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function NewPostPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl">새 글 작성</CardTitle>
      </CardHeader>
      <CardContent>
        <PostForm action={createPostAction} cancelHref="/" submitLabel="등록" />
      </CardContent>
    </Card>
  );
}
