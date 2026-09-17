-- Apply once through the Supabase SQL editor or migration runner.
-- Isolated schemas; no changes to existing public tables or auth users.
begin;

create schema institute;
create schema institute_private;
revoke all on schema institute, institute_private from public, anon;
grant usage on schema institute to authenticated, service_role;
grant usage on schema institute_private to authenticated;

create table institute.students (
  id uuid primary key default gen_random_uuid(),
  auth_user_id uuid unique references auth.users(id) on delete set null,
  student_id text not null unique check (length(student_id) between 1 and 64),
  email text not null unique check (email = lower(email) and length(email) <= 254),
  status text not null default 'pending' check (status in ('active', 'inactive', 'pending')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table institute.courses (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique check (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
  title text not null,
  status text not null check (status in ('active', 'coming_soon', 'archived')),
  total_weeks integer not null default 5 check (total_weeks between 1 and 52),
  created_at timestamptz not null default now()
);

create table institute.enrollments (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references institute.students(id) on delete cascade,
  course_id uuid not null references institute.courses(id) on delete cascade,
  status text not null default 'active' check (status in ('active', 'inactive', 'pending')),
  created_at timestamptz not null default now(),
  unique (student_id, course_id)
);
create index enrollments_course_id_idx on institute.enrollments(course_id);

create table institute.lessons (
  id uuid primary key default gen_random_uuid(),
  course_id uuid not null references institute.courses(id) on delete cascade,
  week_number integer not null check (week_number between 1 and 52),
  title text not null default 'PLACEHOLDER',
  description text not null default 'PLACEHOLDER',
  notes text not null default 'PLACEHOLDER',
  reflection_questions text not null default 'PLACEHOLDER',
  status text not null default 'locked' check (status in ('published', 'locked')),
  display_order integer not null,
  unique (course_id, week_number)
);

create function institute_private.touch_student()
returns trigger language plpgsql set search_path = '' as $$
begin
  new.updated_at = now();
  return new;
end;
$$;
create trigger students_updated_at before update on institute.students
for each row execute function institute_private.touch_student();

-- Definer helpers use fully qualified names, accept no identity argument, and
-- derive the requesting identity only from the signed Supabase JWT.
create function institute_private.session_is_live()
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from auth.sessions s
    where s.user_id = (select auth.uid())
      and s.id::text = (select auth.jwt() ->> 'session_id')
  );
$$;

create function institute_private.active_student_id()
returns uuid language sql stable security definer set search_path = '' as $$
  select s.id from institute.students s
  where s.auth_user_id = (select auth.uid())
    and s.status = 'active'
    and institute_private.session_is_live();
$$;

create function institute_private.can_read_course(requested_course uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from institute.enrollments e
    join institute.courses c on c.id = e.course_id
    where e.student_id = institute_private.active_student_id()
      and e.course_id = requested_course
      and e.status = 'active' and c.status = 'active'
  );
$$;

revoke all on all functions in schema institute_private from public, anon, authenticated;
grant execute on function institute_private.session_is_live() to authenticated;
grant execute on function institute_private.active_student_id() to authenticated;
grant execute on function institute_private.can_read_course(uuid) to authenticated;

alter table institute.students enable row level security;
alter table institute.courses enable row level security;
alter table institute.enrollments enable row level security;
alter table institute.lessons enable row level security;

-- Explicit grants prevent an inherited/default PostgREST grant from widening access.
revoke all on all tables in schema institute from public, anon, authenticated;
grant select (id, auth_user_id, student_id, status) on institute.students to authenticated;
grant select (id, slug, title, status, total_weeks, created_at) on institute.courses to authenticated;
grant select (id, student_id, course_id, status) on institute.enrollments to authenticated;
grant select (id, course_id, week_number, title, description, notes, reflection_questions,
              status, display_order) on institute.lessons to authenticated;
grant all on all tables in schema institute to service_role;

create policy student_reads_own_record on institute.students for select to authenticated
using (auth_user_id = (select auth.uid()) and (select institute_private.session_is_live()));

create policy student_reads_available_courses on institute.courses for select to authenticated
using (
  (status = 'coming_soon' and (select institute_private.active_student_id()) is not null)
  or institute_private.can_read_course(id)
);

create policy student_reads_own_enrollments on institute.enrollments for select to authenticated
using (student_id = (select institute_private.active_student_id()));

create policy enrolled_student_reads_published_lessons on institute.lessons
for select to authenticated
using (status = 'published' and institute_private.can_read_course(course_id));

-- No client INSERT/UPDATE/DELETE policies or grants. Provision through trusted admin access.
insert into institute.courses (slug, title, status, total_weeks) values
  ('architecture-of-the-mind', 'Architecture of the Mind', 'active', 5),
  ('future-course', 'Future Course', 'coming_soon', 5);

insert into institute.lessons
  (course_id, week_number, title, status, display_order)
select c.id, w,
  case when w = 1 then 'Mind Over Matter' else 'PLACEHOLDER' end,
  case when w = 1 then 'published' else 'locked' end, w
from institute.courses c cross join generate_series(1, 5) w
where c.slug = 'architecture-of-the-mind';

notify pgrst, 'reload schema';
commit;
