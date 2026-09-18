-- Keep result validation authoritative in the database for existing deployments.

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
    select value::bigint from jsonb_array_elements_text(p_impostor_player_ids)
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
    (select string_agg(value, ',' order by value)
       from jsonb_array_elements_text(p_impostor_player_ids)),
    p_screenshot_url
  ) returning * into v_sub;

  update public.matches
     set status = 'RESULT_PENDING', result_submitted_by = p_submitted_by
   where id = p_match_id;
  return next v_sub;
end;
$$;

revoke execute on function public.submit_match_result(bigint, bigint, bigint, text, jsonb, text)
  from public, anon, authenticated;
grant execute on function public.submit_match_result(bigint, bigint, bigint, text, jsonb, text)
  to service_role;
