-- Make result submission, approval, rejection, Elo and player statistics atomic.

create unique index if not exists uq_result_submissions_pending_match
  on public.result_submissions(match_id)
  where status = 'PENDING';

create or replace function public.submit_match_result(
  p_guild_id bigint,
  p_match_id bigint,
  p_submitted_by bigint,
  p_winner_side text,
  p_impostor_player_ids jsonb,
  p_screenshot_url text
)
returns setof public.result_submissions
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_sub public.result_submissions%rowtype;
  v_match public.matches%rowtype;
  v_impostor_id bigint;
begin
  if p_winner_side not in ('CREWMATE', 'IMPOSTOR') then
    raise exception 'Invalid winner side';
  end if;
  if p_screenshot_url is null or btrim(p_screenshot_url) = '' then
    raise exception 'Screenshot is required';
  end if;
  if p_impostor_player_ids is null
     or jsonb_typeof(p_impostor_player_ids) <> 'array' then
    raise exception 'Impostor players must be a JSON array';
  end if;
  if jsonb_array_length(p_impostor_player_ids) not between 1 and 3 then
    raise exception 'Impostor player count must be between 1 and 3';
  end if;
  if jsonb_array_length(p_impostor_player_ids) <>
     (select count(distinct value) from jsonb_array_elements_text(p_impostor_player_ids)) then
    raise exception 'Impostor players must be unique';
  end if;

  select * into v_match from public.matches
   where id = p_match_id and guild_id = p_guild_id
   for update;
  if not found then
    raise exception 'Match not found in guild';
  end if;
  if v_match.result_processed or v_match.status not in ('READY', 'IN_PROGRESS') then
    raise exception 'Match does not accept result submissions';
  end if;
  if not exists (
    select 1 from public.match_players mp
    join public.players p on p.id = mp.player_id
    where mp.match_id = p_match_id and p.discord_user_id = p_submitted_by
  ) then
    raise exception 'Submitter is not a match player';
  end if;

  for v_impostor_id in
    select distinct value::bigint from jsonb_array_elements_text(p_impostor_player_ids)
  loop
    if not exists (
      select 1 from public.match_players
      where match_id = p_match_id and player_id = v_impostor_id
    ) then
      raise exception 'Impostor player % is not in match', v_impostor_id;
    end if;
  end loop;

  insert into public.result_submissions
    (guild_id, match_id, submitted_by, winner_side, impostor_player_ids, screenshot_url)
  values (
    p_guild_id,
    p_match_id,
    p_submitted_by,
    p_winner_side,
    coalesce((select string_agg(value, ',' order by value)
      from jsonb_array_elements_text(p_impostor_player_ids)), ''),
    p_screenshot_url
  ) returning * into v_sub;

  update public.matches
     set status = 'RESULT_PENDING', result_submitted_by = p_submitted_by
   where id = p_match_id;
  return next v_sub;
end;
$$;

create or replace function public.approve_match_result(
  p_match_id bigint,
  p_approved_by bigint,
  p_win_elo integer,
  p_loss_elo integer
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_sub public.result_submissions%rowtype;
  v_match public.matches%rowtype;
  v_mp public.match_players%rowtype;
  v_player public.players%rowtype;
  v_impostors bigint[] := '{}'::bigint[];
  v_role text;
  v_delta integer;
  v_after integer;
  v_won boolean;
begin
  select * into v_sub from public.result_submissions
   where match_id = p_match_id and status = 'PENDING'
   order by id limit 1 for update;
  if not found then
    raise exception 'No pending result submission for match %', p_match_id;
  end if;

  select * into v_match from public.matches where id = p_match_id for update;
  if not found or v_match.result_processed then
    raise exception 'Match missing or already processed';
  end if;

  if nullif(v_sub.impostor_player_ids, '') is not null then
    select array_agg(value::bigint) into v_impostors
      from unnest(string_to_array(v_sub.impostor_player_ids, ',')) value;
  end if;

  for v_mp in
    select * from public.match_players where match_id = p_match_id order by id for update
  loop
    select * into strict v_player from public.players
     where id = v_mp.player_id and guild_id = v_match.guild_id for update;
    v_role := case when v_mp.player_id = any(v_impostors)
                   then 'IMPOSTOR' else 'CREWMATE' end;
    v_won := v_role = v_sub.winner_side;
    v_delta := case when v_won then p_win_elo else p_loss_elo end;
    v_after := v_player.elo + v_delta;

    update public.players
       set elo = v_after,
           peak_elo = greatest(peak_elo, v_after),
           matches = matches + 1,
           wins = wins + case when v_won then 1 else 0 end,
           losses = losses + case when v_won then 0 else 1 end,
           win_streak = case when v_won then win_streak + 1 else 0 end,
           best_win_streak = case when v_won
             then greatest(best_win_streak, win_streak + 1) else best_win_streak end,
           updated_at = now()
     where id = v_player.id;

    update public.match_players
       set role_side = v_role,
           elo_before = v_player.elo,
           elo_delta = v_delta,
           elo_after = v_after,
           result = case when v_won then 'WIN' else 'LOSS' end
     where id = v_mp.id;

    insert into public.elo_transactions
      (guild_id, player_id, match_id, old_elo, change, new_elo, reason,
       transaction_type, created_by)
    values
      (v_match.guild_id, v_player.id, p_match_id, v_player.elo, v_delta, v_after,
       format('Match %s', v_sub.winner_side), 'MATCH', p_approved_by);
  end loop;

  insert into public.match_results
    (match_id, winner_side, screenshot_url, submitted_by, approved_by, approved_at)
  values
    (p_match_id, v_sub.winner_side, v_sub.screenshot_url,
     v_sub.submitted_by, p_approved_by, now());

  update public.result_submissions
     set status = 'APPROVED', approved_by = p_approved_by, approved_at = now()
   where id = v_sub.id;
  update public.matches
     set status = 'COMPLETED', winner_side = v_sub.winner_side,
         result_processed = true, result_approved_by = p_approved_by,
         finished_at = now()
   where id = p_match_id;
end;
$$;

create or replace function public.reject_match_result(
  p_match_id bigint,
  p_rejected_by bigint
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_submission_id bigint;
begin
  select id into v_submission_id from public.result_submissions
   where match_id = p_match_id and status = 'PENDING'
   order by id limit 1 for update;
  if not found then
    raise exception 'No pending result submission for match %', p_match_id;
  end if;

  update public.result_submissions
     set status = 'REJECTED', approved_by = p_rejected_by, approved_at = now()
   where id = v_submission_id;
  update public.matches
     set status = 'IN_PROGRESS', result_submitted_by = null
   where id = p_match_id and result_processed = false;
end;
$$;

revoke execute on function public.submit_match_result(bigint, bigint, bigint, text, jsonb, text)
  from public, anon, authenticated;
revoke execute on function public.approve_match_result(bigint, bigint, integer, integer)
  from public, anon, authenticated;
revoke execute on function public.reject_match_result(bigint, bigint)
  from public, anon, authenticated;
grant execute on function public.submit_match_result(bigint, bigint, bigint, text, jsonb, text)
  to service_role;
grant execute on function public.approve_match_result(bigint, bigint, integer, integer)
  to service_role;
grant execute on function public.reject_match_result(bigint, bigint) to service_role;
