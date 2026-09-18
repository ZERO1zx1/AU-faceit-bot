-- Add proper rejection tracking to result_submissions and support an optional
-- rejection reason. The old reject RPC reused approved_by/approved_at for
-- rejections; this migration adds dedicated rejected_by/rejected_at/rejection_reason
-- columns and a reason-aware reject_match_result function.

alter table public.result_submissions
  add column if not exists rejected_by bigint,
  add column if not exists rejected_at timestamptz,
  add column if not exists rejection_reason text;

create or replace function public.reject_match_result(
  p_match_id    bigint,
  p_rejected_by bigint,
  p_reason      text default null
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_sub public.result_submissions%rowtype;
  v_match public.matches%rowtype;
begin
  select * into v_sub from public.result_submissions
   where match_id = p_match_id and status = 'PENDING'
   order by id limit 1 for update;
  if not found then
    raise exception 'No pending result submission for match %', p_match_id;
  end if;

  select * into v_match from public.matches where id = p_match_id for update;
  if not found then
    raise exception 'Match missing for result rejection';
  end if;
  if v_match.result_processed then
    raise exception 'Match is already processed';
  end if;

  update public.result_submissions
     set status = 'REJECTED',
         rejected_by = p_rejected_by,
         rejected_at = now(),
         rejection_reason = nullif(btrim(coalesce(p_reason, '')), ''),
         approved_by = null,
         approved_at = null
   where id = v_sub.id;

  update public.matches
     set status = 'IN_PROGRESS', result_submitted_by = null
   where id = p_match_id;
end;
$$;

-- The legacy 2-argument reject overload is dropped so callers cannot use the
-- audit-free path. Idempotent on databases that already ran the old migration.
drop function if exists public.reject_match_result(bigint, bigint);
revoke execute on function public.reject_match_result(bigint, bigint, text) from public, anon, authenticated;

grant execute on function public.reject_match_result(bigint, bigint, text) to service_role;