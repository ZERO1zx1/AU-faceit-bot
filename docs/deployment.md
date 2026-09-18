# AU FACEIT Bot Production Deployment Guide

This guide describes a conservative production deployment for the AU FACEIT Discord bot at commit `b0d868d`. The bot requires Python 3.12 or newer, a Discord application, and a Supabase project. The deployment uses the server-only Supabase `service_role` key and must never expose that key to Discord users, browser clients, or source control.

## 1. Production prerequisites

Prepare a Linux host or container runtime with Docker Engine and Compose support, or install Python 3.12+ directly. Create a Discord application and bot in the [Discord Developer Portal](https://discord.com/developers/applications). Enable the bot intents required by this project: **Server Members Intent**, **Message Content Intent**, and the voice-state intent used by the application. The bot also needs the permissions listed in `README.md`, including Manage Roles, Manage Channels, Move Members, Send Messages, Embed Links, and View Channels. Discord gateway intents control which event categories a bot receives, so the application settings and the code configuration must agree (see [discord.py Intents](https://discordpy.readthedocs.io/en/latest/intents.html)).

Create a Supabase project and keep its URL and `service_role` key in a secret manager or a protected environment file. The service-role key bypasses normal client-side restrictions and must be treated as a server credential. Do not put it in a Docker image layer, public repository, frontend bundle, or issue report.

## 2. Clone and pin the release

Use a deployment checkout rather than running from a developer workspace:

```bash
git clone https://github.com/ZERO1zx1/AU-faceit-bot.git
cd AU-faceit-bot
git checkout b0d868d5176180928f185a54d3c37af6e71c0b68
```

The release should be reviewed before deployment. Confirm that the working tree is clean and record the commit in the deployment change record.

## 3. Configure environment variables

Create `.env` from the example file and set real values only on the server:

```
DISCORD_TOKEN=replace_with_the_bot_token
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=replace_with_the_server_only_service_role_key
ENVIRONMENT=production
LOG_LEVEL=INFO
FACEIT_API_KEY=
```

The application also supports matchmaking defaults such as `DEFAULT_ELO`, `WIN_ELO`, `LOSS_ELO`, `QUEUE_SIZE`, and `NICKNAME_FORMAT` through pydantic-settings. Guild-specific settings created by `/setup server` take precedence for matchmaking behavior. Keep `ENVIRONMENT=production` and use `LOG_LEVEL=INFO` unless temporary incident diagnostics require a more verbose level.

Set restrictive permissions on the environment file:

```bash
chmod 600 .env
```

Before starting, verify that the required secrets are non-empty without printing their values:

```bash
python3 - <<'PY'
from pathlib import Path
from dotenv import dotenv_values

values = dotenv_values(Path('.env'))
for name in ('DISCORD_TOKEN', 'SUPABASE_URL', 'SUPABASE_KEY'):
    if not values.get(name):
        raise SystemExit(f'{name} is missing')
print('Required production settings are present.')
PY
```

## 4. Apply the database schema and migrations

The repository contains a base schema followed by six ordered migrations. Apply them to a staging Supabase project first, then apply the same sequence to production. Supabase describes migrations as versioned SQL changes that can be tracked and deployed consistently (see [Supabase Database Migrations](https://supabase.com/docs/guides/deployment/database-migrations)).

Run the base schema once using the Supabase SQL editor or an approved migration process:

```
supabase/schema.sql
```

Then apply these files in lexical order:

```
supabase/migrations/20260911061007_harden_queue_and_rpc_security.sql
supabase/migrations/20260911150000_persistent_result_views.sql
supabase/migrations/20260911152000_atomic_result_lifecycle.sql
supabase/migrations/20260911200000_cleanup_match_channels.sql
supabase/migrations/20260913000000_validate_result_impostors.sql
supabase/migrations/20260913120000_result_rejection_fields.sql
```

The migration sequence enables row-level security, restricts mutation RPCs to `service_role`, adds atomic queue and result operations, persists result-view bindings, validates screenshot and impostor data, adds channel cleanup configuration, and records auditable result rejection fields. Do not apply migrations out of order. Take a database backup or use the platform's approved recovery point before production schema changes.

This repository was statically audited, but live SQL execution against a Supabase project was not performed in the local validation session. Perform a staging migration and verify the RPC signatures before production use.

## 5. Run with Docker

Build and start the bot using the supplied image:

```bash
docker compose up --build -d
```

View startup logs:

```bash
docker compose logs -f --tail=200
```

The container starts `python -m app.bot`. A successful startup should initialize the Supabase client, load every required cog, restore persistent views, start the leaderboard task, and synchronize application commands. Treat extension-load failures, missing credentials, and failed database initialization as deployment failures.

For a host-managed deployment without Docker:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m app.bot
```

Use a process supervisor such as systemd, Docker Compose restart policy, or an equivalent service manager. Do not use an unmonitored shell session for production operation.

## 6. First Discord-server setup

Invite the bot to the target server with the required scopes and permissions. Run the commands in this order:

1. `/setup server` creates the registered role and match category and stores guild defaults.

1. `/setup logs <channel>` configures the visible audit-log channel.

1. `/setup levels` creates Level 1–10 roles and Elo boundaries.

1. `/setup register [channel]` publishes the persistent registration panel.

1. `/setup queue [channel]` publishes the persistent queue panel.

1. `/setup leaderboard <channel>` configures the persistent leaderboard message.

Register a test account, verify that the role and optional nickname are applied, join and leave the queue, and confirm that audit events appear. Then use a staging or test group to exercise full match provisioning, result submission, approval, rejection, channel cleanup, and voice tracking.

Unregister is a **soft deactivation**. It sets `players.active=false` and retains match, Elo, voice, and audit history. A later registration reactivates the existing player record instead of creating a new historical identity. An active queue entry or active match blocks unregister.

## 7. Operational checks

After each deployment, verify the following conditions:

- The process remains running after startup and after a Discord reconnect.

- Slash commands appear in the target server or after the expected global command propagation delay.

- Persistent registration and queue buttons continue working after a restart.

- Pending result approval buttons are restored after a restart.

- Queue claims create only one match under concurrent button presses.

- A failed channel creation removes any partially created channels and requeues players.

- Result approval changes Elo and statistics once, while rejection returns the match to `IN_PROGRESS` and stores the rejection actor and reason.

- Voice sessions are closed safely during restart recovery.

- Leaderboard refresh updates the configured message.

Use the local validation commands before every release:

```bash
DISCORD_TOKEN=test-token pytest -q
ruff check app tests scripts
mypy app tests scripts
python3 -m compileall -q app tests scripts
git diff --check
pip-audit -r requirements.txt
```

The current release passed the first five checks locally. The dependency scan on the resolved environment reported no known vulnerabilities. Live Discord and Supabase checks remain deployment responsibilities.

## 8. Secrets, backups, and incident response

Rotate the Discord token and Supabase service-role key through their respective administrative consoles if either may have been exposed. Rebuild the image after rotation and restart the service. Do not attempt to conceal a leaked secret by editing only the latest commit; remove it from all reachable history and invalidate it.

Keep database backups and a documented rollback path. Application rollback and database rollback are separate operations: an older bot binary may not understand newer schema fields, and a database rollback may lose accepted results. Test the rollback procedure in staging.

Collect logs without including tokens, authorization headers, or full database URLs with credentials. The application writes persistent error details to `logs/cogs.txt` when configured by the logging module. Restrict access to those logs because Discord IDs and operational details may be present.