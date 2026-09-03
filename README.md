# AU FACEIT Bot

Multi-server Discord Among Us competitive matchmaking platform.

## Features

- **Multi-server isolation** — each Discord server has its own configuration, player database, queue, matches, Elo, and leaderboard via `guild_id`.
- **Registration** — `/setup-register` creates a persistent REGISTER panel; players complete a modal and get an auto-assigned role + nickname.
- **Player profiles** — `/profile`, `/matches`, Elo history tracking.
- **Elo system** — configurable win/loss Elo, atomic 15-player transactions, full audit history.
- **FACEIT-style levels 1–10** — custom boundaries per server, automatic role assignment and removal.
- **Queue** — `/setup-queue` persistent ENTER MATCH / LEAVE QUEUE panel with duplicate prevention.
- **Matchmaking** — 15/15 triggers atomic match creation with random CALL assignment, private text + voice channels, and permission locking.
- **Results** — Crewmate/Impostor result submission, screenshot evidence, admin approval, atomic Elo update, anti-abuse protection.
- **Leaderboard** — `/setup-leaderboard` and `/leaderboard` with auto-refresh via message editing.
- **Voice tracking** — join/leave/move tracking with per-player voice time in profiles.
- **Custom panels** — `panel create` / `panel delete` management.
- **Full logging** — structured audit logs for register, queue, match, result, elo, level, error.

## Tech Stack

- Python 3.12+
- discord.py 2.x
- SQLAlchemy 2.x (async) + asyncpg
- Alembic (migrations)
- PostgreSQL

## Setup

1. Set up a Discord application + bot and store the token.

2. Create a `.env` file (see `.env.example`):

```dotenv
DISCORD_TOKEN=your_bot_token_here
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/au_faceit
ENVIRONMENT=development
LOG_LEVEL=INFO
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run migrations:

```bash
alembic upgrade head
```

5. Start the bot:

```bash
python -m app.bot
```

Or with Docker:

```bash
docker compose up --build
```

## Development

```bash
ruff check .
pytest
alembic upgrade head
```

## Commands

Player: `/profile`, `/matches`, `/leaderboard`, `/unregister`
Panels: REGISTER, ENTER MATCH, LEAVE QUEUE, SUBMIT RESULT

Admin: `setup-server`, `setup-register`, `setup-faceit-level`, `setup-leaderboard`, `setup-queue`, `result`, `player elo`, `player ban`, `player unban`, `panel create`, `panel delete`

## Project Structure

```
app/
├── bot.py            # entry point
├── config.py         # pydantic-settings
├── db.py             # async engine + session factory
├── logging.py        # logging config
├── cogs/             # discord interaction layer
├── services/         # business logic
├── repositories/     # data access
├── models/           # SQLAlchemy ORM models
├── ui/               # embeds, views, modals, selects
├── tasks/            # background tasks
└── utils/            # helpers, validation, permissions
migrations/           # alembic
scripts/              # command sync
tests/
```
