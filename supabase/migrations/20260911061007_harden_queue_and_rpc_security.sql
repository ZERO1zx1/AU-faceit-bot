-- Harden the server-only Data API boundary and atomically claim one match
-- worth of eligible queue entries. The Discord bot must use service_role.

create or replace function public.claim_match_from_queue(p_guild_id bigint)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_queue_size integer;
  v_ids bigint[];
  v_match public.matches%rowtype;
  v_seq bigint;
  v_elo integer;
  v_sum integer := 0;
  v_count integer := 0;
  v_pid bigint;
begin
  select gs.queue_size
    into v_queue_size
    from public.guild_settings as gs
   where gs.guild_id = p_guild_id;

  if v_queue_size is null or v_queue_size < 1 then
    raise exception 'Valid guild settings not found for guild %', p_guild_id;
  end if;

  select array_agg(claimed.player_id order by claimed.joined_at, claimed.id)
    into v_ids
    from (
      select q.id, q.player_id, q.joined_at
        from public.queue_entries as q
        join public.players as p
          on p.id = q.player_id
         and p.guild_id = q.guild_id
       where q.guild_id = p_guild_id
         and q.status = 'WAITING'
         and p.active = true
         and p.banned = false
       order by q.joined_at, q.id
       limit v_queue_size
       for update of q skip locked
    ) as claimed;

  if cardinality(coalesce(v_ids, '{}'::bigint[])) < v_queue_size then
    return null;
  end if;

  v_seq := nextval('public.match_display_seq');
  insert into public.matches (guild_id, display_id, status)
  values (p_guild_id, format('AU-%08s', v_seq), 'CREATING')
  returning * into v_match;

  for v_pid in select unnest(v_ids) order by random()
  loop
    select p.elo
      into strict v_elo
      from public.players as p
     where p.id = v_pid
       and p.guild_id = p_guild_id
       and p.active = true
       and p.banned = false;
    v_sum := v_sum + v_elo;
    v_count := v_count + 1;
    insert into public.match_players (match_id, player_id, call_number, elo_before)
    values (v_match.id, v_pid, v_count, v_elo);
  end loop;

  delete from public.queue_entries as q
   where q.guild_id = p_guild_id
     and q.status = 'WAITING'
     and q.player_id = any(v_ids);

  update public.matches
     set average_elo = v_sum / v_count
   where id = v_match.id
  returning * into v_match;

  return jsonb_build_object(
    'match', to_jsonb(v_match),
    'player_ids', to_jsonb(v_ids)
  );
end;
$$;

alter function public.pop_queue_entries(bigint) set search_path = '';
alter function public.create_match(bigint, jsonb) set search_path = '';
alter function public.apply_match_result(bigint, jsonb, text, integer, integer, bigint, bigint)
  set search_path = '';
alter function public.submit_match_result(bigint, bigint, bigint, text, jsonb, text)
  set search_path = '';
alter function public.approve_match_result(bigint, bigint, integer, integer)
  set search_path = '';

alter table public.guilds enable row level security;
alter table public.guild_settings enable row level security;
alter table public.players enable row level security;
alter table public.level_roles enable row level security;
alter table public.queue_entries enable row level security;
alter table public.matches enable row level security;
alter table public.elo_transactions enable row level security;
alter table public.match_players enable row level security;
alter table public.match_results enable row level security;
alter table public.result_submissions enable row level security;
alter table public.voice_sessions enable row level security;
alter table public.voice_totals enable row level security;
alter table public.panels enable row level security;
alter table public.audit_logs enable row level security;
alter table public.bans enable row level security;
alter table public.cooldowns enable row level security;

revoke all on all tables in schema public from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;
grant select, insert, update, delete on all tables in schema public to service_role;
grant usage, select on all sequences in schema public to service_role;

revoke execute on function public.pop_queue_entries(bigint) from public, anon, authenticated;
revoke execute on function public.claim_match_from_queue(bigint) from public, anon, authenticated;
revoke execute on function public.create_match(bigint, jsonb) from public, anon, authenticated;
revoke execute on function public.apply_match_result(bigint, jsonb, text, integer, integer, bigint, bigint) from public, anon, authenticated;
revoke execute on function public.submit_match_result(bigint, bigint, bigint, text, jsonb, text) from public, anon, authenticated;
revoke execute on function public.approve_match_result(bigint, bigint, integer, integer) from public, anon, authenticated;

grant execute on function public.pop_queue_entries(bigint) to service_role;
grant execute on function public.claim_match_from_queue(bigint) to service_role;
grant execute on function public.create_match(bigint, jsonb) to service_role;
grant execute on function public.apply_match_result(bigint, jsonb, text, integer, integer, bigint, bigint) to service_role;
grant execute on function public.submit_match_result(bigint, bigint, bigint, text, jsonb, text) to service_role;
grant execute on function public.approve_match_result(bigint, bigint, integer, integer) to service_role;
