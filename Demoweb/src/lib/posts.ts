import "server-only";

import { neon } from "@neondatabase/serverless";

import { DEFAULT_CATEGORY, isCategory, type Category } from "@/lib/categories";

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

export type PostSummary = Omit<Post, "content" | "comments"> & { commentCount: number };

export { CATEGORIES, type Category } from "@/lib/categories";

export const PAGE_SIZE = 10;

if (!process.env.DATABASE_URL) {
  throw new Error("DATABASE_URL이 설정되지 않았습니다. .env.local을 확인하세요.");
}
const sql = neon(process.env.DATABASE_URL);

type Row = Record<string, unknown>;

const iso = (value: unknown) => new Date(value as string | Date).toISOString();

function toSummary(row: Row): PostSummary {
  const category = String(row.category);
  return {
    id: Number(row.id),
    title: String(row.title),
    author: String(row.author),
    // 이전 분류(자유·질문·정보 등)로 저장된 글은 기본 분류로 표시
    category: isCategory(category) ? category : DEFAULT_CATEGORY,
    views: Number(row.views),
    createdAt: iso(row.created_at),
    updatedAt: iso(row.updated_at),
    commentCount: Number(row.comment_count ?? 0),
  };
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
  const q = query.trim();
  const pattern = `%${q.replace(/[\\%_]/g, "\\$&")}%`;
  const cat = category || null;
  const search = q || null;

  const [{ total }] = await sql`
    SELECT count(*)::int AS total FROM posts
    WHERE (${cat}::text IS NULL OR category = ${cat})
      AND (${search}::text IS NULL OR title ILIKE ${pattern} OR content ILIKE ${pattern} OR author ILIKE ${pattern})`;

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const current = Math.min(Math.max(1, page), totalPages);

  const rows = await sql`
    SELECT p.id, p.title, p.author, p.category, p.views, p.created_at, p.updated_at,
           (SELECT count(*) FROM comments c WHERE c.post_id = p.id)::int AS comment_count
    FROM posts p
    WHERE (${cat}::text IS NULL OR p.category = ${cat})
      AND (${search}::text IS NULL OR p.title ILIKE ${pattern} OR p.content ILIKE ${pattern} OR p.author ILIKE ${pattern})
    ORDER BY (p.category = '공지') DESC, p.id DESC
    LIMIT ${PAGE_SIZE} OFFSET ${(current - 1) * PAGE_SIZE}`;

  return { posts: rows.map(toSummary), total: Number(total), page: current, totalPages };
}

export async function getPost(id: number): Promise<Post | null> {
  if (!Number.isInteger(id)) return null;
  const [rows, comments] = await sql.transaction([
    sql`SELECT * FROM posts WHERE id = ${id}`,
    sql`SELECT id, author, content, created_at FROM comments WHERE post_id = ${id} ORDER BY created_at`,
  ]);
  if (rows.length === 0) return null;

  const { commentCount: _, ...summary } = toSummary(rows[0]);
  return {
    ...summary,
    content: String(rows[0].content),
    comments: comments.map((c) => ({
      id: String(c.id),
      author: String(c.author),
      content: String(c.content),
      createdAt: iso(c.created_at),
    })),
  };
}

export async function incrementViews(id: number) {
  if (!Number.isInteger(id)) return;
  await sql`UPDATE posts SET views = views + 1 WHERE id = ${id}`;
}

export async function createPost(input: Pick<Post, "title" | "content" | "author" | "category">) {
  const [row] = await sql`
    INSERT INTO posts (title, content, author, category)
    VALUES (${input.title}, ${input.content}, ${input.author}, ${input.category})
    RETURNING id`;
  return { id: Number(row.id) };
}

export async function updatePost(id: number, input: Pick<Post, "title" | "content" | "category">) {
  await sql`
    UPDATE posts
    SET title = ${input.title}, content = ${input.content}, category = ${input.category}, updated_at = now()
    WHERE id = ${id}`;
}

export async function deletePost(id: number) {
  await sql`DELETE FROM posts WHERE id = ${id}`;
}

export async function addComment(postId: number, input: Pick<Comment, "author" | "content">) {
  await sql`
    INSERT INTO comments (post_id, author, content)
    SELECT id, ${input.author}, ${input.content} FROM posts WHERE id = ${postId}`;
}

export async function deleteComment(postId: number, commentId: string) {
  await sql`DELETE FROM comments WHERE id = ${commentId}::uuid AND post_id = ${postId}`;
}
