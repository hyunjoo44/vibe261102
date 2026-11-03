"use client";

import { useActionState } from "react";
import Link from "next/link";

import type { FormState } from "@/app/actions";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { CATEGORIES, DEFAULT_CATEGORY } from "@/lib/categories";

type Props = {
  action: (prev: FormState, formData: FormData) => Promise<FormState>;
  defaults?: { title: string; content: string; author: string; category: string };
  cancelHref: string;
  submitLabel: string;
  isEdit?: boolean;
};

function FieldError({ message }: { message?: string }) {
  return message ? <p className="text-sm text-destructive">{message}</p> : null;
}

export function PostForm({ action, defaults, cancelHref, submitLabel, isEdit }: Props) {
  const [state, formAction, pending] = useActionState(action, {});
  const values = state.values ?? defaults;
  const errors = state.errors ?? {};

  return (
    <form action={formAction} className="flex flex-col gap-5">
      <div className="grid gap-5 sm:grid-cols-2">
        <div className="flex flex-col gap-2">
          <Label htmlFor="category">카테고리</Label>
          <select
            id="category"
            name="category"
            defaultValue={values?.category ?? DEFAULT_CATEGORY}
            className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <FieldError message={errors.category} />
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor="author">작성자</Label>
          <Input
            id="author"
            name="author"
            defaultValue={values?.author}
            disabled={isEdit}
            placeholder="이름을 입력하세요"
            aria-invalid={!!errors.author}
          />
          <FieldError message={errors.author} />
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="title">제목</Label>
        <Input
          id="title"
          name="title"
          defaultValue={values?.title}
          placeholder="제목을 입력하세요"
          aria-invalid={!!errors.title}
        />
        <FieldError message={errors.title} />
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="content">내용</Label>
        <Textarea
          id="content"
          name="content"
          defaultValue={values?.content}
          placeholder="내용을 입력하세요"
          className="min-h-64"
          aria-invalid={!!errors.content}
        />
        <FieldError message={errors.content} />
      </div>

      <div className="flex justify-end gap-2">
        <Link href={cancelHref} className={buttonVariants({ variant: "outline" })}>
          취소
        </Link>
        <Button type="submit" disabled={pending}>
          {pending ? "저장 중..." : submitLabel}
        </Button>
      </div>
    </form>
  );
}
