-- Guilds can choose whether match channels (text/voice) are deleted after a
-- result is approved. Defaults to true (current behaviour) on existing servers.

alter table public.guild_settings
  add column if not exists cleanup_match_channels boolean not null default true;