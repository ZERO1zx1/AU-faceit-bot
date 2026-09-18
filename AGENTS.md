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
| `pytest` | Run all 31+ async tests |
| `python -m mypy app/ tests/` | Type-check with Mypy strict |
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
- **Atomic operations** use Postgres RPC functions defined in `supabase/schema.sql`. Migrations in `supabase/migrations/` must be applied in order (see README `Migration Order`).
- **Tests use** `FakeSupabaseClient` (`tests/fake_supabase.py`) — in-memory mock. No external services needed for unit tests.
- **Discord intents** required in `app/bot.py`: `default`, `message_content`, `members`, `voice_states`.
- **Bot permissions**: `Manage Roles`, `Manage Channels`, `Move Members`, `Send Messages`, `Embed Links`, `View Channels`.
- **Lint/typecheck**: `ruff check` then `mypy`. Fix lint before commit.
- **Env loading**: `.env` read by `config.py`. Never commit `.env`.

## Gotchas & Pitfalls

- **Migration order is critical** — applying out of order breaks RLS policies and unique indexes. Always apply migrations sequentially from `supabase/migrations/`.
- **`person_from_faker` vs `person` sampler**: Data Designer `person` requires downloaded managed datasets; `person_from_faker` is the fallback when assets aren't available (see `data-designer/` skill).
- **Ruff config**: `target-version = "py312"`, `line-length = 100`. `select = ["E", "F", "W", "I", "N", "UP", "B", "SIM"]`.
- **Docker**: `docker compose up --build` builds and starts both the bot and Supabase. Use for integration env.
- **Live testing required**: `/setup server`, `/setup register`, `/setup queue`, `/setup levels`, match channel creation, and voice tracking need a real Discord server to verify.