"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import {
  CATEGORIES,
  addComment,
  createPost,
  deleteComment,
  deletePost,
  updatePost,
  type Category,
} from "@/lib/posts";

export type FormState = {
  errors?: Partial<Record<"title" | "content" | "author" | "category", string>>;
  values?: Record<string, string>;
};

function field(formData: FormData, name: string) {
  return String(formData.get(name) ?? "").trim();
}

function validatePost(formData: FormData, requireAuthor: boolean) {
  const values = {
    title: field(formData, "title"),
    content: field(formData, "content"),
    author: field(formData, "author"),
    category: field(formData, "category"),
  };
  const errors: NonNullable<FormState["errors"]> = {};

  if (!values.title) errors.title = "제목을 입력해 주세요.";
  else if (values.title.length > 100) errors.title = "제목은 100자 이내로 입력해 주세요.";
  if (!values.content) errors.content = "내용을 입력해 주세요.";
  if (requireAuthor && !values.author) errors.author = "작성자를 입력해 주세요.";
  if (!CATEGORIES.includes(values.category as Category))
    errors.category = "카테고리를 선택해 주세요.";

  return { values, errors, ok: Object.keys(errors).length === 0 };
}

export async function createPostAction(
  _prev: FormState,
  formData: FormData
): Promise<FormState> {
  const { values, errors, ok } = validatePost(formData, true);
  if (!ok) return { errors, values };

  const post = await createPost({
    title: values.title,
    content: values.content,
    author: values.author,
    category: values.category as Category,
  });
  revalidatePath("/");
  redirect(`/posts/${post.id}`);
}

export async function updatePostAction(
  id: number,
  _prev: FormState,
  formData: FormData
): Promise<FormState> {
  const { values, errors, ok } = validatePost(formData, false);
  if (!ok) return { errors, values };

  await updatePost(id, {
    title: values.title,
    content: values.content,
    category: values.category as Category,
  });
  revalidatePath("/");
  revalidatePath(`/posts/${id}`);
  redirect(`/posts/${id}`);
}

export async function deletePostAction(id: number) {
  await deletePost(id);
  revalidatePath("/");
  redirect("/");
}

export async function addCommentAction(postId: number, formData: FormData) {
  const author = field(formData, "author");
  const content = field(formData, "content");
  if (!author || !content) return;

  await addComment(postId, { author, content });
  revalidatePath(`/posts/${postId}`);
}

export async function deleteCommentAction(postId: number, commentId: string) {
  await deleteComment(postId, commentId);
  revalidatePath(`/posts/${postId}`);
}
