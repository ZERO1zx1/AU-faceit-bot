-- Persist result approval message bindings so button callbacks survive restarts.
alter table public.result_submissions
  add column if not exists approval_message_id bigint;

revoke all on table public.result_submissions from anon, authenticated;
grant select, insert, update, delete on table public.result_submissions to service_role;
