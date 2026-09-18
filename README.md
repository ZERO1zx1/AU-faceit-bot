# AU FACEIT Bot

Multi-server Discord Among Us competitive matchmaking platform.

## Features

- **Multi-server isolation** — each Discord server has its own configuration, player database, queue, matches, Elo, and leaderboard via `guild_id`.
- **Registration** — `/setup register` creates a persistent REGISTER panel; players complete a modal and get an auto-assigned role + nickname. Unregister is a **soft deactivation**: the row keeps its Elo/level/history, re-registration restores everything, and the player's Among Us name stays reserved per guild (only the original owner can reuse it).
- **Player profiles** — `/profile`, `/matches`, Elo history tracking.
- **Elo system** — configurable win/loss Elo, atomic 15-player transactions, full audit history.
- **FACEIT-style levels 1–10** — custom boundaries per server, automatic role assignment and removal after every result approval or manual Elo change.
- **Queue** — `/setup queue` persistent ENTER MATCH / LEAVE QUEUE panel with duplicate prevention and active-match guard.
- **Matchmaking** — 15/15 triggers atomic match creation with random CALL assignment, private text + voice channels, permission locking, and rollback on partial channel creation failure.
- **Results** — Crewmate/Impostor result submission, screenshot evidence, admin approval, atomic Elo update + player stats, anti-abuse protection. Moderators (guild owner or a role with `Manage Server`) can also reject a submission with a mandatory reason; a rejected result is locked against approval for auditability.
- **Leaderboard** — `/setup leaderboard` with auto-refresh background task every 12 minutes.
- **Voice tracking** — join/leave/move tracking with per-player voice time; stale sessions auto-closed on restart.
- **Custom panels** — `/panel create`, `/panel edit`, `/panel delete`, `/panel list` with full embed validation.
- **Full logging** — structured audit logs for register, unregister, queue join/leave, match create/start/end, result submit/approve/reject, elo changes, and level changes.

## Tech Stack

- Python 3.12+
- discord.py 2.6+
- Supabase (PostgREST REST API via `supabase-py` AsyncClient)
  - All persistence flows through the service → repository → Supabase layer
  - Tables + atomic Postgres RPC functions live in `supabase/schema.sql`
- PostgreSQL (managed by Supabase)
- pytest + pytest-asyncio (in-memory fake Supabase client)

## Setup

1. Set up a Discord application + bot and store the token.

2. Create a Supabase project. From **Project Settings → API**, copy the **Project URL**
   and the server-only **service_role** key. Never expose this key in a client application.

3. In the Supabase SQL editor, run `supabase/schema.sql` — this creates all tables
   and the critical Postgres RPC functions needed for atomic operations. Then apply
   every file in `supabase/migrations/` **in order** (see Migration Order below). The
   final migration (`20260913120000_result_rejection_fields.sql`) is required for the
   moderator result-rejection flow — apply all six before deploying the current code.

4. Create a `.env` file (see `.env.example`):

```dotenv
DISCORD_TOKEN=your_bot_token_here
SUPABASE_URL=https://your_project_ref.supabase.co
SUPABASE_KEY=your_supabase_service_role_key
ENVIRONMENT=development
LOG_LEVEL=INFO
FACEIT_API_KEY=optional_faceit_api_key
```

`FACEIT_API_KEY` is optional; leave blank or omit to skip FACEIT integration.

5. Install dependencies:

```bash
pip install -r requirements.txt
```

6. Start the bot:

```bash
python -m app.bot
```

Or with Docker:

```bash
docker compose up --build
```

## Development

```bash
ruff check app/ tests/ scripts/
pytest                       # 67 tests, all async, in-memory fake Supabase (no live services)
python -m mypy app tests scripts
```

The full check workflow is: `ruff check` → `mypy` → `pytest` → `compileall`. Skip
live Discord/Supabase entirely — unit tests run against `tests/fake_supabase.py`.

## Discord Intents

The bot requires the following intents (configured in `app/bot.py`):

- `default` (includes `guilds`)
- `message_content`
- `members` (required for member role management and nickname changes)
- `voice_states` (required for voice session tracking)

## Required Bot Permissions

Grant the bot the following permissions in the server (or via role):

- `Manage Roles` — assign registered and level roles
- `Manage Channels` — create match text/voice channels and clean them up after completion
- `Move Members` — move players into match voice channels
- `Send Messages` — send panels, results, and log messages
- `Embed Links` — send rich embeds
- `View Channels` — required for all channel interactions

Slash commands that require admin access enforce `Manage Server` or `Administrator` permission at the Discord API level.

## Commands

All commands are slash commands (registered globally on startup).

### Player

| Command | Description |
|---------|-------------|
| `/profile [member]` | View your or another player's profile |
| `/matches [member]` | View a player's Elo history (last 20) |
| `/leaderboard` | Top 10 players by Elo |
| `/queue-status` | Current queue count and average Elo |
| `/unregister` | Deactivate your registration with confirmation (soft delete; re-registering restores your Elo/level/history)
| `/help` | Show all available commands |
| `/result submit` | Submit a match result (with screenshot + impostors) |

### Admin

| Command | Description |
|---------|-------------|
| `/setup server` | Create registered role + match category |
| `/setup logs <channel>` | Set the audit log channel |
| `/setup register [channel]` | Deploy the registration panel |
| `/setup levels` | Create Level 1–10 roles with Elo boundaries |
| `/setup queue [channel]` | Deploy the queue panel |
| `/setup leaderboard <channel>` | Set the leaderboard channel |
| `/panel create` | Create a custom embed panel |
| `/panel edit` | Edit a custom embed panel |
| `/panel delete` | Delete a custom embed panel |
| `/panel list` | List all custom panels |
| `/admin elo <member> <amount>` | Manual Elo adjustment |
| `/admin ban <member> [reason]` | Ban a player |
| `/admin unban <member>` | Unban a player |
| `/result review <match_id>` | Review a pending/completed result |
| `/result approve` | Approve a pending result (button) — lock + settle Elo in one atomic RPC |
| `/result reject` | Reject a pending result with a reason (button) — requires guild owner or `Manage Server` role |

## Migration Order

After a fresh `supabase/schema.sql`, apply migrations in order:

1. `20260911061007_harden_queue_and_rpc_security.sql` — queue claim queue_size enforcement, voice_totals RLS, pop_queue_entries RPC, security hardening
2. `20260911150000_persistent_result_views.sql` — `result_submissions` RLS + approval message tracking
3. `20260911152000_atomic_result_lifecycle.sql` — atomic submit/approve/reject RPCs with partial unique index
4. `20260911200000_cleanup_match_channels.sql` — `guild_settings.cleanup_match_channels` column
5. `20260913000000_validate_result_impostors.sql` — enforce screenshot evidence and 1–3 unique impostors
6. `20260913120000_result_rejection_fields.sql` — rejection audit columns + reason-aware `reject_match_result(bigint, bigint, text)`; drops the legacy 2-argument reject overload

Migrations are idempotent; the final one must run before the bot's result-rejection
features are used.

## Project Structure

```
app/
├── bot.py              # entry point, background tasks, recovery
├── config.py           # pydantic-settings (env-based config)
├── supabase_client.py  # Supabase async client singleton
├── logging.py          # structured logging config
├── cogs/               # slash command + listener layer (no direct DB access)
├── services/           # business logic (service → repository/RPC only)
├── repositories/       # Supabase REST data access
├── models/             # Pydantic models (table shapes)
├── ui/                 # embeds, views, modals, selects, panel builder
├── tasks/              # background tasks (leaderboard refresh)
└── utils/              # helpers, validation, permission checks
supabase/
├── schema.sql          # tables + critical Postgres RPC functions
└── migrations/         # incremental migration files
tests/
├── conftest.py         # FakeSupabaseClient fixture
├── fake_supabase.py    # in-memory Supabase mock (PostgREST + RPC)
└── test_*.py           # pytest (67 tests, all async, fake Supabase)
scripts/
└── sync_commands.py    # sync slash commands to Discord API
```

## Residual Risk / Remaining Live Verification

- `/setup server`, `/setup register`, `/setup queue`, `/setup levels` should be tested live in a Discord server to confirm role creation, channel permissions, and panel message delivery.
- `panel create` / `panel edit` should be tested live to confirm embed rendering and message editing.
- Match channel creation + rollback should be tested live with a real guild category.
- Voice tracking recovery should be tested by restarting the bot while a user is in a voice channel.
- Background leaderboard refresh should be verified by waiting 12 minutes and confirming the message edits.
- Database migrations should be applied in a staging Supabase project before production.
- SQL security is verified by static tests only (SECURITY DEFINER + `search_path = ''` +
  revoke/grant posture). The RPC functions have **not** been executed against a live
  Supabase project — run them through a staging deploy before production.
