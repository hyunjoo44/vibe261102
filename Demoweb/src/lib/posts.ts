import "server-only";

import { promises as fs } from "fs";
import path from "path";
import { randomUUID } from "crypto";

export type Comment = {
  id: string;
  author: string;
  content: string;
  createdAt: string;
};

export type Post = {
  id: number;
  title: string;
  content: string;
  author: string;
  category: Category;
  views: number;
  createdAt: string;
  updatedAt: string;
  comments: Comment[];
};

export const CATEGORIES = ["자유", "질문", "정보", "공지"] as const;
export type Category = (typeof CATEGORIES)[number];

export const PAGE_SIZE = 10;

const DATA_DIR = path.join(process.cwd(), "data");
const DATA_FILE = path.join(DATA_DIR, "posts.json");

const SEED: Post[] = [
  {
    id: 1,
    title: "게시판에 오신 것을 환영합니다",
    content:
      "Next.js, shadcn/ui, TypeScript로 만든 게시판입니다.\n\n글 작성, 수정, 삭제, 검색, 댓글 기능을 사용해 보세요.",
    author: "관리자",
    category: "공지",
    views: 0,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    comments: [],
  },
];

async function readAll(): Promise<Post[]> {
  try {
    const raw = await fs.readFile(DATA_FILE, "utf-8");
    return JSON.parse(raw) as Post[];
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    await writeAll(SEED);
    return SEED;
  }
}

async function writeAll(posts: Post[]) {
  await fs.mkdir(DATA_DIR, { recursive: true });
  await fs.writeFile(DATA_FILE, JSON.stringify(posts, null, 2), "utf-8");
}

export async function listPosts({
  query = "",
  category,
  page = 1,
}: {
  query?: string;
  category?: string;
  page?: number;
}) {
  const posts = await readAll();
  const q = query.trim().toLowerCase();

  const filtered = posts
    .filter((p) => !category || p.category === category)
    .filter(
      (p) =>
        !q ||
        p.title.toLowerCase().includes(q) ||
        p.content.toLowerCase().includes(q) ||
        p.author.toLowerCase().includes(q)
    )
    .sort((a, b) => {
      // 공지는 항상 상단에 고정
      if (a.category === "공지" && b.category !== "공지") return -1;
      if (b.category === "공지" && a.category !== "공지") return 1;
      return b.id - a.id;
    });

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(Math.max(1, page), totalPages);

  return {
    posts: filtered.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE),
    total: filtered.length,
    page: current,
    totalPages,
  };
}

export async function getPost(id: number) {
  const posts = await readAll();
  return posts.find((p) => p.id === id) ?? null;
}

export async function incrementViews(id: number) {
  const posts = await readAll();
  const post = posts.find((p) => p.id === id);
  if (!post) return;
  post.views += 1;
  await writeAll(posts);
}

export async function createPost(
  input: Pick<Post, "title" | "content" | "author" | "category">
) {
  const posts = await readAll();
  const now = new Date().toISOString();
  const post: Post = {
    ...input,
    id: posts.reduce((max, p) => Math.max(max, p.id), 0) + 1,
    views: 0,
    createdAt: now,
    updatedAt: now,
    comments: [],
  };
  posts.push(post);
  await writeAll(posts);
  return post;
}

export async function updatePost(
  id: number,
  input: Pick<Post, "title" | "content" | "category">
) {
  const posts = await readAll();
  const post = posts.find((p) => p.id === id);
  if (!post) return null;
  Object.assign(post, input, { updatedAt: new Date().toISOString() });
  await writeAll(posts);
  return post;
}

export async function deletePost(id: number) {
  const posts = await readAll();
  await writeAll(posts.filter((p) => p.id !== id));
}

export async function addComment(
  postId: number,
  input: Pick<Comment, "author" | "content">
) {
  const posts = await readAll();
  const post = posts.find((p) => p.id === postId);
  if (!post) return null;
  post.comments.push({
    ...input,
    id: randomUUID(),
    createdAt: new Date().toISOString(),
  });
  await writeAll(posts);
  return post;
}

export async function deleteComment(postId: number, commentId: string) {
  const posts = await readAll();
  const post = posts.find((p) => p.id === postId);
  if (!post) return;
  post.comments = post.comments.filter((c) => c.id !== commentId);
  await writeAll(posts);
}
