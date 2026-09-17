// Disposable PostgreSQL policy test. Does not contact or modify Supabase.
// Usage: node tests/institute/check_rls.mjs /absolute/path/to/pglite/dist/index.js
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const { PGlite } = await import(process.argv[2] || "@electric-sql/pglite");
const db = new PGlite();
let checks = 0;
await db.exec(`
  create role anon; create role authenticated; create role service_role bypassrls;
  create schema auth;
  create table auth.users (id uuid primary key, email text);
  create table auth.sessions (id uuid primary key, user_id uuid references auth.users(id));
  create function auth.jwt() returns jsonb language sql stable as $$
    select nullif(current_setting('request.jwt.claims', true), '')::jsonb;
  $$;
  create function auth.uid() returns uuid language sql stable as $$
    select (auth.jwt()->>'sub')::uuid;
  $$;
  grant usage on schema auth to authenticated;
`);
await db.exec(
  await readFile(
    new URL(
      "../../supabase/migrations/202609160001_institute.sql",
      import.meta.url,
    ),
    "utf8",
  ),
);
const alice = "a0000000-0000-0000-0000-000000000001";
const bob = "b0000000-0000-0000-0000-000000000001";
const sid = "c0000000-0000-0000-0000-000000000001";
await db.exec(`
  insert into auth.users values ('${alice}', 'alice@example.com'), ('${bob}', 'bob@example.com');
  insert into auth.sessions values ('${sid}', '${alice}');
  insert into institute.students (auth_user_id, student_id, email, status)
    values ('${alice}', 'RI-001', 'alice@example.com', 'active'),
           ('${bob}', 'RI-002', 'bob@example.com', 'active');
  insert into institute.enrollments (student_id, course_id)
    select s.id, c.id from institute.students s cross join institute.courses c
    where c.status = 'active';
  insert into institute.courses (slug, title, status) values ('other-course', 'Other', 'active');
  insert into institute.lessons (course_id, week_number, title, status, display_order)
    select id, 1, 'PRIVATE OTHER COURSE', 'published', 1 from institute.courses where slug = 'other-course';
  update institute.lessons set notes = 'PRIVATE LOCKED NOTES' where week_number > 1;
`);

async function asStudent() {
  await db.exec("set role authenticated");
  await db.query(`select set_config('request.jwt.claims', $1, false)`, [
    JSON.stringify({ sub: alice, session_id: sid }),
  ]);
}
async function expectRows(sql, count, description) {
  const result = await db.query(sql);
  assert.equal(result.rows.length, count, description);
  checks++;
}
async function denied(sql, description) {
  await assert.rejects(() => db.query(sql), { code: "42501" }, description);
  checks++;
}
await asStudent();
await expectRows(
  "select id, student_id from institute.students",
  1,
  "Only own student record",
);
await expectRows(
  "select id from institute.students where student_id = 'RI-002'",
  0,
  "Other student denied",
);
await denied(
  "select email from institute.students",
  "Private admin columns denied",
);
await expectRows(
  "select id from institute.courses",
  2,
  "Own course plus coming soon",
);
await expectRows(
  "select id from institute.enrollments",
  1,
  "Only own enrollment",
);
await expectRows(
  "select id from institute.lessons",
  1,
  "Only published enrolled lesson",
);
await expectRows(
  "select notes from institute.lessons where notes = 'PRIVATE LOCKED NOTES'",
  0,
  "Locked payload absent",
);
await expectRows(
  "select id from institute.lessons where title = 'PRIVATE OTHER COURSE'",
  0,
  "Cross-course access denied",
);
await denied(
  "update institute.students set status = 'active'",
  "Cannot approve oneself",
);
await denied(
  "insert into institute.enrollments(student_id, course_id) select id, gen_random_uuid() from institute.students",
  "Cannot enroll oneself",
);
await db.exec(
  `reset role; update institute.enrollments set status = 'inactive' where student_id = (select id from institute.students where student_id = 'RI-001')`,
);
await asStudent();
await expectRows(
  "select id from institute.lessons",
  0,
  "Enrollment revocation immediate",
);
await db.exec(
  `reset role; update institute.enrollments set status = 'active'; update institute.students set status = 'inactive' where student_id = 'RI-001'`,
);
await asStudent();
await expectRows(
  "select id from institute.students",
  1,
  "Inactive student can read own access status",
);
await expectRows(
  "select id from institute.courses",
  0,
  "Inactive student cannot read courses",
);
await expectRows(
  "select id from institute.lessons",
  0,
  "Inactive student cannot read lessons",
);
await db.exec(
  `reset role; update institute.students set status = 'active'; delete from auth.sessions where id = '${sid}'`,
);
await asStudent();
await expectRows(
  "select id from institute.students",
  0,
  "Revoked session denied",
);
await expectRows(
  "select id from institute.lessons",
  0,
  "Old JWT cannot read lessons after logout",
);
await db.exec("reset role; set role anon");
await denied(
  "select id from institute.courses",
  "Anonymous database access denied",
);
await db.close();
console.log(`${checks} PostgreSQL RLS checks passed.`);
