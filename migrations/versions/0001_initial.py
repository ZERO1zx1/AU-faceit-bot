"""Initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "guilds",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "guild_settings",
        sa.Column("guild_id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("admin_role_id", sa.BigInteger(), nullable=True),
        sa.Column("moderator_role_id", sa.BigInteger(), nullable=True),
        sa.Column("registered_role_id", sa.BigInteger(), nullable=True),
        sa.Column("register_channel_id", sa.BigInteger(), nullable=True),
        sa.Column("register_message_id", sa.BigInteger(), nullable=True),
        sa.Column("queue_channel_id", sa.BigInteger(), nullable=True),
        sa.Column("queue_message_id", sa.BigInteger(), nullable=True),
        sa.Column("leaderboard_channel_id", sa.BigInteger(), nullable=True),
        sa.Column("leaderboard_message_id", sa.BigInteger(), nullable=True),
        sa.Column("match_category_id", sa.BigInteger(), nullable=True),
        sa.Column("log_channel_id", sa.BigInteger(), nullable=True),
        sa.Column("default_elo", sa.Integer(), server_default=sa.text("1000"), nullable=False),
        sa.Column("win_elo", sa.Integer(), server_default=sa.text("8"), nullable=False),
        sa.Column("loss_elo", sa.Integer(), server_default=sa.text("-6"), nullable=False),
        sa.Column("queue_size", sa.Integer(), server_default=sa.text("15"), nullable=False),
        sa.Column("nickname_format", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "players",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("discord_user_id", sa.BigInteger(), nullable=False),
        sa.Column("among_us_name", sa.String(100), nullable=False),
        sa.Column("nickname", sa.Text(), nullable=True),
        sa.Column("faceit_player_id", sa.String(64), nullable=True),
        sa.Column("faceit_nickname", sa.String(100), nullable=True),
        sa.Column("elo", sa.Integer(), server_default=sa.text("1000"), nullable=False),
        sa.Column("peak_elo", sa.Integer(), server_default=sa.text("1000"), nullable=False),
        sa.Column("level", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("matches", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("wins", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("losses", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("win_streak", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("best_win_streak", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_voice_seconds", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("registered_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("banned", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("guild_id", "discord_user_id", name="uq_players_guild_user"),
        sa.UniqueConstraint("guild_id", "among_us_name", name="uq_players_guild_amongus"),
    )
    op.create_index("ix_players_guild_id", "players", ["guild_id"])
    op.create_index("ix_players_discord_user_id", "players", ["discord_user_id"])

    op.create_table(
        "level_roles",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("min_elo", sa.Integer(), nullable=True),
        sa.Column("max_elo", sa.Integer(), nullable=True),
        sa.Column("role_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("guild_id", "level", name="uq_level_roles_guild_level"),
    )
    op.create_index("ix_level_roles_guild_id", "level_roles", ["guild_id"])

    op.create_table(
        "matches",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("display_id", sa.String(32), nullable=False),
        sa.Column("status", sa.String(20), server_default=sa.text("'CREATING'"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("text_channel_id", sa.BigInteger(), nullable=True),
        sa.Column("voice_channel_id", sa.BigInteger(), nullable=True),
        sa.Column("average_elo", sa.Integer(), nullable=True),
        sa.Column("winner_side", sa.String(20), nullable=True),
        sa.Column("result_submitted_by", sa.BigInteger(), nullable=True),
        sa.Column("result_approved_by", sa.BigInteger(), nullable=True),
        sa.Column("result_processed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_matches_guild_id", "matches", ["guild_id"])
    op.create_unique_constraint("uq_matches_display_id", "matches", ["display_id"])
    op.create_index("ix_matches_display_id", "matches", ["display_id"])

    op.create_table(
        "match_players",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("match_id", sa.BigInteger(), nullable=False),
        sa.Column("player_id", sa.BigInteger(), nullable=False),
        sa.Column("call_number", sa.Integer(), nullable=False),
        sa.Column("role_side", sa.String(20), nullable=True),
        sa.Column("elo_before", sa.Integer(), nullable=True),
        sa.Column("elo_delta", sa.Integer(), nullable=True),
        sa.Column("elo_after", sa.Integer(), nullable=True),
        sa.Column("result", sa.String(20), nullable=True),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("match_id", "player_id", name="uq_match_players_match_player"),
        sa.UniqueConstraint("match_id", "call_number", name="uq_match_players_match_call"),
    )
    op.create_index("ix_match_players_match_id", "match_players", ["match_id"])

    op.create_table(
        "match_results",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("match_id", sa.BigInteger(), nullable=False),
        sa.Column("winner_side", sa.String(20), nullable=False),
        sa.Column("screenshot_url", sa.Text(), nullable=True),
        sa.Column("submitted_by", sa.BigInteger(), nullable=False),
        sa.Column("approved_by", sa.BigInteger(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("match_id", name="uq_match_results_match"),
    )

    op.create_table(
        "result_submissions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("match_id", sa.BigInteger(), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("submitted_by", sa.BigInteger(), nullable=False),
        sa.Column("winner_side", sa.String(20), nullable=False),
        sa.Column("impostor_player_ids", sa.Text(), nullable=False),
        sa.Column("screenshot_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), server_default=sa.text("'PENDING'"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_result_submissions_match_id", "result_submissions", ["match_id"])
    op.create_index("ix_result_submissions_guild_id", "result_submissions", ["guild_id"])

    op.create_table(
        "elo_transactions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("player_id", sa.BigInteger(), nullable=False),
        sa.Column("match_id", sa.BigInteger(), nullable=True),
        sa.Column("old_elo", sa.Integer(), nullable=False),
        sa.Column("change", sa.Integer(), nullable=False),
        sa.Column("new_elo", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(100), nullable=True),
        sa.Column("transaction_type", sa.String(32), server_default=sa.text("'MATCH'"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("match_id", "player_id", "transaction_type", name="uq_elo_tx_match_player_type"),
    )
    op.create_index("ix_elo_transactions_guild_id", "elo_transactions", ["guild_id"])
    op.create_index("ix_elo_transactions_player_id", "elo_transactions", ["player_id"])

    op.create_table(
        "queue_entries",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("player_id", sa.BigInteger(), nullable=False),
        sa.Column("joined_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("queue_position", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), server_default=sa.text("'WAITING'"), nullable=False),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("guild_id", "player_id", "status", name="uq_queue_guild_player"),
    )
    op.create_index("ix_queue_entries_guild_id", "queue_entries", ["guild_id"])
    op.create_index("ix_queue_entries_player_id", "queue_entries", ["player_id"])

    op.create_table(
        "voice_sessions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("player_id", sa.BigInteger(), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("joined_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("left_at", sa.DateTime(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_voice_sessions_guild_id", "voice_sessions", ["guild_id"])
    op.create_index("ix_voice_sessions_player_id", "voice_sessions", ["player_id"])

    op.create_table(
        "voice_totals",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("player_id", sa.BigInteger(), nullable=False),
        sa.Column("bucket_date", sa.Date(), nullable=False),
        sa.Column("total_seconds", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("guild_id", "player_id", "bucket_date", name="uq_voice_totals_bucket"),
    )
    op.create_index("ix_voice_totals_guild_id", "voice_totals", ["guild_id"])
    op.create_index("ix_voice_totals_player_id", "voice_totals", ["player_id"])

    op.create_table(
        "voice_totals",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("player_id", sa.BigInteger(), nullable=False),
        sa.Column("bucket_date", sa.Date(), nullable=False),
        sa.Column("total_seconds", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("guild_id", "player_id", "bucket_date", name="uq_voice_totals_bucket"),
    )
    op.create_index("ix_voice_totals_guild_id", "voice_totals", ["guild_id"])
    op.create_index("ix_voice_totals_player_id", "voice_totals", ["player_id"])

    op.create_table(
        "panels",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=True),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("color", sa.Integer(), nullable=True),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("footer", sa.String(200), nullable=True),
        sa.Column("configuration_json", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_panels_guild_id", "panels", ["guild_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("action_type", sa.String(30), nullable=False),
        sa.Column("actor_id", sa.BigInteger(), nullable=True),
        sa.Column("target_entity", sa.String(50), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("success", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_audit_logs_guild_id", "audit_logs", ["guild_id"])
    op.create_index("ix_audit_logs_action_type", "audit_logs", ["action_type"])

    op.create_table(
        "bans",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("player_id", sa.BigInteger(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("banned_by", sa.BigInteger(), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("banned_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("unbanned_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_bans_guild_id", "bans", ["guild_id"])

    op.create_table(
        "cooldowns",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_cooldowns_guild_id", "cooldowns", ["guild_id"])


def downgrade() -> None:
    op.drop_table("cooldowns")
    op.drop_table("bans")
    op.drop_table("audit_logs")
    op.drop_table("panels")
    op.drop_table("voice_totals")
    op.drop_table("voice_sessions")
    op.drop_table("queue_entries")
    op.drop_table("elo_transactions")
    op.drop_table("result_submissions")
    op.drop_table("match_results")
    op.drop_table("match_players")
    op.drop_table("matches")
    op.drop_table("level_roles")
    op.drop_table("players")
    op.drop_table("guild_settings")
    op.drop_table("guilds")