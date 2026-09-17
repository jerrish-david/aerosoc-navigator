-- Run as the trusted project administrator after creating the Auth user.
-- Replace the two values below. This transaction refuses duplicate provisioning.
begin;
do $$
declare
  approved_email text := 'REPLACE_WITH_APPROVED_EMAIL';
  institute_student_id text := 'REPLACE_WITH_STUDENT_ID';
  auth_id uuid;
  student_uuid uuid;
  course_uuid uuid;
begin
  if approved_email = 'REPLACE_WITH_APPROVED_EMAIL'
    or institute_student_id = 'REPLACE_WITH_STUDENT_ID' then
    raise exception 'Set the approved student email and student ID before running';
  end if;
  approved_email := lower(trim(approved_email));
  select id into strict auth_id from auth.users where lower(email) = approved_email;
  select id into strict course_uuid from institute.courses
    where slug = 'architecture-of-the-mind' and status = 'active';
  insert into institute.students (auth_user_id, student_id, email, status)
    values (auth_id, institute_student_id, approved_email, 'active') returning id into student_uuid;
  insert into institute.enrollments (student_id, course_id, status)
    values (student_uuid, course_uuid, 'active');
end;
$$;
commit;
