// 테이블을 만들고, 비어 있으면 data/posts.json(없으면 환영 글)을 넣는다.
// 실행: npm run db:setup
import { existsSync, readFileSync } from "fs";
import path from "path";
import { neon } from "@neondatabase/serverless";

const sql = neon(process.env.DATABASE_URL);

await sql`
  CREATE TABLE IF NOT EXISTS posts (
    id         SERIAL PRIMARY KEY,
    title      TEXT NOT NULL,
    content    TEXT NOT NULL,
    author     TEXT NOT NULL,
    category   TEXT NOT NULL,
    views      INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
  )`;
await sql`
  CREATE TABLE IF NOT EXISTS comments (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id    INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    author     TEXT NOT NULL,
    content    TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
  )`;
await sql`CREATE INDEX IF NOT EXISTS comments_post_id_idx ON comments(post_id)`;

const [{ count }] = await sql`SELECT count(*)::int AS count FROM posts`;
if (count > 0) {
  console.log(`posts 테이블에 이미 ${count}개의 글이 있어 데이터 이관을 건너뜁니다.`);
  process.exit(0);
}

const jsonFile = path.join(process.cwd(), "data", "posts.json");
const CATEGORIES = ["공지", "스케줄", "사진"];

if (existsSync(jsonFile)) {
  const posts = JSON.parse(readFileSync(jsonFile, "utf-8"));
  const queries = [];
  for (const p of posts) {
    const category = CATEGORIES.includes(p.category) ? p.category : "스케줄";
    queries.push(sql`
      INSERT INTO posts (id, title, content, author, category, views, created_at, updated_at)
      VALUES (${p.id}, ${p.title}, ${p.content}, ${p.author}, ${category}, ${p.views}, ${p.createdAt}, ${p.updatedAt})`);
    for (const c of p.comments ?? []) {
      queries.push(sql`
        INSERT INTO comments (id, post_id, author, content, created_at)
        VALUES (${c.id}, ${p.id}, ${c.author}, ${c.content}, ${c.createdAt})`);
    }
  }
  queries.push(sql`SELECT setval('posts_id_seq', (SELECT max(id) FROM posts))`);
  await sql.transaction(queries);
  console.log(`data/posts.json에서 글 ${posts.length}개를 이관했습니다.`);
} else {
  await sql`
    INSERT INTO posts (title, content, author, category)
    VALUES ('게시판에 오신 것을 환영합니다',
            ${"Next.js, shadcn/ui, TypeScript로 만든 게시판입니다.\n\n글 작성, 수정, 삭제, 검색, 댓글 기능을 사용해 보세요."},
            '관리자', '공지')`;
  console.log("환영 글을 추가했습니다.");
}
