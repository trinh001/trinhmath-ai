-- NEXUS MATH BANK — SUPABASE POSTGRES MIGRATION (MVP)
-- Chạy một lần trong Supabase > SQL Editor. Không dán mật khẩu/API secret vào SQL.
-- Bảng gốc luôn chỉ dành cho admin, học sinh chỉ xem qua các VIEW không lộ đáp án.

create extension if not exists pgcrypto;

create table if not exists public.admins (
  user_id uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now()
);
alter table public.admins enable row level security;
revoke all on public.admins from public, anon, authenticated;

create or replace function public.is_admin()
returns boolean
language sql stable security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.admins where user_id = (select auth.uid())
  );
$$;
revoke all on function public.is_admin() from public, anon, authenticated;
grant execute on function public.is_admin() to authenticated;

create table if not exists public.questions (
  id uuid primary key default gen_random_uuid(),
  stem text not null check (char_length(trim(stem)) > 0),
  image_url text,
  grade integer not null check (grade between 9 and 12),
  chapter text not null default '',
  lesson text not null default '',
  difficulty text not null default 'TH' check (difficulty in ('NB','TH','VD')),
  q_type text not null default 'mcq' check (q_type in ('mcq','tf','short','essay')),
  options jsonb not null default '[]'::jsonb check (jsonb_typeof(options) = 'array'),
  answer jsonb,
  explanation text not null default '',
  source text not null default '',
  status text not null default 'pending' check (status in ('pending','review','approved')),
  created_by uuid references auth.users(id) default auth.uid(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint options_count check ((q_type in ('mcq','tf') and jsonb_array_length(options)=4) or (q_type in ('short','essay')))
);
create table if not exists public.exams (
  id uuid primary key default gen_random_uuid(),
  title text not null check (char_length(trim(title)) > 0),
  grade integer not null check (grade between 9 and 12),
  duration_minutes integer not null default 0 check(duration_minutes between 0 and 300),
  question_ids uuid[] not null default array[]::uuid[],
  status text not null default 'draft' check(status in ('draft','published')),
  created_at timestamptz not null default now()
);
create or replace function public.touch_question_updated_at()
returns trigger language plpgsql set search_path = '' as $$
begin new.updated_at = now(); return new; end $$;
drop trigger if exists trg_question_updated_at on public.questions;
create trigger trg_question_updated_at before update on public.questions
for each row execute procedure public.touch_question_updated_at();

alter table public.questions enable row level security;
alter table public.exams enable row level security;
revoke all on public.questions from public, anon, authenticated;
revoke all on public.exams from public, anon, authenticated;
grant select, insert, update, delete on public.questions to authenticated;
grant select, insert, update, delete on public.exams to authenticated;

-- Chỉ admin được truy cập bảng đầy đủ bao gồm đáp án và bản chờ duyệt.
drop policy if exists admin_questions_select on public.questions;
create policy admin_questions_select on public.questions for select to authenticated using (public.is_admin());
drop policy if exists admin_questions_insert on public.questions;
create policy admin_questions_insert on public.questions for insert to authenticated with check (public.is_admin());
drop policy if exists admin_questions_update on public.questions;
create policy admin_questions_update on public.questions for update to authenticated using (public.is_admin()) with check (public.is_admin());
drop policy if exists admin_questions_delete on public.questions;
create policy admin_questions_delete on public.questions for delete to authenticated using (public.is_admin());

drop policy if exists admin_exams_select on public.exams;
create policy admin_exams_select on public.exams for select to authenticated using (public.is_admin());
drop policy if exists admin_exams_insert on public.exams;
create policy admin_exams_insert on public.exams for insert to authenticated with check (public.is_admin());
drop policy if exists admin_exams_update on public.exams;
create policy admin_exams_update on public.exams for update to authenticated using (public.is_admin()) with check (public.is_admin());
drop policy if exists admin_exams_delete on public.exams;
create policy admin_exams_delete on public.exams for delete to authenticated using (public.is_admin());

-- Views công khai chỉ xuất câu ĐÃ DUYỆT và KHÔNG gửi đáp án/lời giải về trình duyệt trước khi nộp.
-- Views mặc định chạy với quyền chủ sở hữu bảng, là chủ ý để công khai các cột an toàn.
create or replace view public.public_questions with (security_barrier=true) as
 select id, stem, image_url, grade, chapter, lesson, difficulty, q_type,
        options, source, status, created_at
 from public.questions where status='approved';
create or replace view public.published_exams with (security_barrier=true) as
 select id, title, grade, duration_minutes, question_ids, status, created_at
 from public.exams where status='published';
revoke all on public.public_questions from public, anon, authenticated;
revoke all on public.published_exams from public, anon, authenticated;
grant select on public.public_questions to anon, authenticated;
grant select on public.published_exams to anon, authenticated;

-- RPC chấm bài, chỉ truy cập được câu hỏi đã duyệt. Tự luận trả về chưa chấm.
-- Đây là luyện tập tự học, không phải hệ thống thi chống gian lận.
create or replace function public.grade_quiz(p_ids uuid[],p_answers jsonb)
returns jsonb
language plpgsql volatile security definer
set search_path = ''
as $$
declare
  v_q public.questions%rowtype;
  v_id uuid;
  v_ans jsonb;
  v_right boolean;
  v_items jsonb := '[]'::jsonb;
  v_correct int:=0;
  v_gradable int:=0;
  v_essay int:=0;
  v_k text;
  v_order int:=0;
begin
  if p_ids is null or coalesce(array_length(p_ids,1),0)<1
     or array_length(p_ids,1)>40
     or p_answers is null or jsonb_typeof(p_answers)<>'object' then
    raise exception 'Dữ liệu bài làm không hợp lệ';
  end if;
  if (select count(distinct u) from unnest(p_ids) as u) <> array_length(p_ids,1) then
    raise exception 'Danh sách câu hỏi bị trùng';
  end if;
  foreach v_id in array p_ids loop
    select * into v_q from public.questions
    where id=v_id and status='approved';
    if not found then raise exception 'Không tìm thấy câu hỏi đã duyệt'; end if;
    v_order:=v_order+1;
    v_ans:=p_answers->(v_id::text);
    v_right:=null;
    if v_q.q_type='mcq' then
      v_right:=(v_ans=v_q.answer and v_ans is not null);
    elsif v_q.q_type='tf' then
      v_right:=true;
      foreach v_k in array array['a','b','c','d'] loop
        if v_ans is null or jsonb_typeof(v_ans)<>'object'
           or not(v_ans ? v_k) or jsonb_typeof(v_ans->v_k)<>'boolean'
           or v_ans->v_k is distinct from v_q.answer->v_k then
          v_right:=false;
        end if;
      end loop;
    elsif v_q.q_type='short' then
      v_right:=(v_ans is not null and jsonb_typeof(v_ans)='string' and
        lower(regexp_replace(btrim(v_ans#>>'{}'),'\s+',' ','g')) =
        lower(regexp_replace(btrim(v_q.answer#>>'{}'),'\s+',' ','g')));
    end if;
    if v_right is null then v_essay:=v_essay+1;
    else
      v_gradable:=v_gradable+1;
      if v_right then v_correct:=v_correct+1; end if;
    end if;
    v_items:=v_items||jsonb_build_array(jsonb_build_object(
      'id',v_q.id,'number',v_order,'correct',v_right,
      'submitted',v_ans,'answer',v_q.answer,'explanation',v_q.explanation
    ));
  end loop;
  return jsonb_build_object('correct',v_correct,'gradable',v_gradable,'essay',v_essay,'results',v_items);
end $$;
revoke all on function public.grade_quiz(uuid[],jsonb) from public, anon, authenticated;
grant execute on function public.grade_quiz(uuid[],jsonb) to anon, authenticated;
revoke all on function public.touch_question_updated_at() from public, anon, authenticated;

-- Bucket công khai CHỈ dành cho ảnh câu hỏi, không tải lên tài liệu mật.
insert into storage.buckets (id,name,public,file_size_limit,allowed_mime_types)
values('math-images','math-images',true,5242880,array['image/jpeg','image/png','image/webp'])
on conflict(id) do update set public=true,file_size_limit=5242880,
 allowed_mime_types=array['image/jpeg','image/png','image/webp'];
drop policy if exists math_images_admin_upload on storage.objects;
create policy math_images_admin_upload on storage.objects
for insert to authenticated with check (bucket_id='math-images' and public.is_admin());
drop policy if exists math_images_admin_update on storage.objects;
create policy math_images_admin_update on storage.objects
for update to authenticated using(bucket_id='math-images' and public.is_admin())
with check(bucket_id='math-images' and public.is_admin());
drop policy if exists math_images_admin_delete on storage.objects;
create policy math_images_admin_delete on storage.objects
for delete to authenticated using(bucket_id='math-images' and public.is_admin());

-- BƯỚC RIÊNG sau khi tạo tài khoản giáo viên trong Supabase > Authentication > Users:
-- Thay email ví dụ bằng email giáo viên đã tạo, bỏ '--' ở đầu dòng rồi Run:
-- insert into public.admins(user_id)
-- select id from auth.users where email='GIAO_VIEN@EXAMPLE.COM'
-- on conflict(user_id) do nothing;
