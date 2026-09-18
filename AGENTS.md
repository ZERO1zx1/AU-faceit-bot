# AGENTS.md — AU Faceit Bot

Compact instructions for working in this Discord matchmaking bot repo.

## Quickstart

```bash
# 1. Copy .env and fill in values
cp .env.example .env

# 2. Install deps
pip install -r requirements.txt

# 3. Start bot
python -m app.bot
```

## Development Commands

| Command | Description |
|---------|-------------|
| `ruff check app/ tests/ scripts/` | Lint (Ruff, py312 target) |
| `pytest` | Run all 71 async tests (in-memory fake Supabase, no live services) |
| `python -m mypy app/ tests/ scripts/` | Type-check with Mypy strict (91 files clean) |
| `pip-audit -r requirements.txt` | Dependency vulnerability scan |
| `docker compose up --build` | Full stack (Postgres + bot) |

## Project Structure (key dirs)

```
app/
├── bot.py              # entry point + background tasks
├── config.py           # pydantic-settings (env-based)
├── supabase_client.py  # Supabase async client singleton
├── services/           # business logic → repository/RPC only
├── repositories/       # Supabase REST data access
├── models/             # Pydantic table-shape models
├── cogs/               # slash commands + listeners
├── scripts/            # utility scripts (sync_commands.py)
└── utils/              # helpers, validation, permissions

supabase/
├── schema.sql          # tables + critical Postgres RPC functions
└── migrations/         # incremental migration SQL files

tests/
├── conftest.py         # FakeSupabaseClient fixture
├── fake_supabase.py    # in-memory Supabase mock
└── test_*.py           # pytest, all async
```

## Critical Conventions

- **All persistence** flows through `service → repository → Supabase RPC`. Never query tables directly.
- **Atomic operations** use Postgres RPC functions defined in `supabase/schema.sql`. Migrations in `supabase/migrations/` must be applied in order (see README `Migration Order`). All six migrations — including `20260913120000_result_rejection_fields.sql`, which drops the legacy 2-argument `reject_match_result` and grants `service_role` the reason-aware 3-argument overload — are required before the current code.
- **Unregister is a soft deactivate** (`registration_service`): queued/active-match players are refused, the row keeps Elo/level/history, re-registration reactivates the same row, and the Among Us name stays reserved per guild (owner can claim it again; others cannot).
- **Result reject** persists `rejected_by`/`rejected_at`/`rejection_reason`; a rejected submission cannot later be approved. Approval/rejection validate guild ownership and are restricted to the guild owner or a `Manage Server` role (`permission_service.is_moderator_member`).
- **Tests use** `FakeSupabaseClient` (`tests/fake_supabase.py`) — in-memory mock. No external services needed for unit tests.
- **Discord intents** required in `app/bot.py`: `default`, `message_content`, `members`, `voice_states`.
- **Bot permissions**: `Manage Roles`, `Manage Channels`, `Move Members`, `Send Messages`, `Embed Links`, `View Channels`.
- **Lint/typecheck**: `ruff check` then `mypy`. Fix lint before commit.
- **Env loading**: `.env` read by `config.py`. Never commit `.env`. `DISCORD_TOKEN` defaults to `""` at import (unit tests run without it); `app/bot.py` raises `RuntimeError` on startup if it is empty.

## Gotchas & Pitfalls

- **Migration order is critical** — applying out of order breaks RLS policies and unique indexes. Always apply migrations sequentially from `supabase/migrations/`.
- **`person_from_faker` vs `person` sampler**: Data Designer `person` requires downloaded managed datasets; `person_from_faker` is the fallback when assets aren't available (see `data-designer/` skill).
- **Ruff config**: `target-version = "py312"`, `line-length = 100`. `select = ["E", "F", "W", "I", "N", "UP", "B", "SIM"]`.
- **Docker**: `docker compose up --build` builds and starts both the bot and Supabase. Use for integration env.
- **Live testing required**: `/setup server`, `/setup register`, `/setup queue`, `/setup levels`, match channel creation, and voice tracking need a real Discord server to verify.