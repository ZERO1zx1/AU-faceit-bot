"""Discord embed builders for all bot panels."""

from datetime import datetime

import discord

from app.utils.helpers import format_elo_change
from app.utils.time import format_duration


def registration_embed(
    *,
    title: str = "AU FACEIT REGISTRATION",
    elo: int = 1000,
    level: int = 4,
    status: str = "Not Registered",
):
    return discord.Embed(
        title=f"━━━ {title} ━━━",
        description=(
            "Among Us competitive matchmaking\nсистемд бүртгүүлнэ үү.\n\n"
            f"ELO       {elo}\n"
            f"LEVEL     {level}\n"
            f"STATUS    {status}"
        ),
        color=discord.Color.blurple(),
    )


def profile_embed(member: discord.Member, player):
    fmt_time = format_duration(player.total_voice_seconds)
    win_rate = (player.wins / player.matches * 100) if player.matches else 0

    embed = discord.Embed(
        title=f"━━━ {player.among_us_name} — AU FACEIT PROFILE ━━━",
        color=discord.Color.gold(),
    )
    embed.add_field(name="Among Us", value=player.among_us_name, inline=True)
    embed.add_field(name="ELO", value=f"{player.elo:,}", inline=True)
    embed.add_field(name="LEVEL", value=str(player.level), inline=True)
    embed.add_field(name="Matches", value=str(player.matches), inline=True)
    embed.add_field(name="Wins", value=str(player.wins), inline=True)
    embed.add_field(name="Losses", value=str(player.losses), inline=True)
    embed.add_field(name="Win Rate", value=f"{win_rate:.1f}%", inline=True)
    embed.add_field(name="Voice Time", value=fmt_time, inline=True)
    embed.add_field(name="Best Elo", value=f"{player.peak_elo:,}", inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"ELO {player.elo:,} | Level {player.level}")
    return embed


def leaderboard_embed(players, guild_name: str = "AU FACEIT"):
    embed = discord.Embed(
        title=f"━━━ {guild_name} LEADERBOARD ━━━",
        color=discord.Color.gold(),
    )
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, p in enumerate(players):
        prefix = medals[i] if i < 3 else f"#{i+1}"
        lines.append(f"{prefix} {p.among_us_name} — ELO {p.elo:,} | LEVEL {p.level}")
    embed.description = "\n".join(lines) if lines else "No players yet."
    embed.set_footer(text=f"Last updated: {datetime.utcnow().strftime('%H:%M')}")
    return embed


def queue_embed(count: int, max_size: int = 15, avg_elo: int = 0):
    status = "WAITING FOR PLAYERS"
    if count >= max_size:
        status = "MATCH STARTING..."
    embed = discord.Embed(
        title="━━━ AU FACEIT QUEUE ━━━",
        description=(
            f"**PLAYERS**\n\n{count} / {max_size}\n\n"
            f"Average Elo\n{avg_elo:,}\n\n"
            f"Status\n**{status}**"
        ),
        color=discord.Color.green(),
    )
    return embed


def match_embed(match, players: list):
    call_lines = []
    for p in players:
        name = (p.player.among_us_name if getattr(p, "player", None) else None) or f"Player #{p.player_id}"
        call_lines.append(f"CALL {p.call_number:02d} — {name}")
    description = "**STATUS**\nIN PROGRESS\n\n**PLAYERS**\n\n" + "\n".join(call_lines)
    if match.average_elo:
        description += f"\n\nAverage Elo\n{match.average_elo:,}"
    embed = discord.Embed(
        title=f"━━━ MATCH {match.display_id} ━━━",
        description=description,
        color=discord.Color.red(),
    )
    created = match.created_at.strftime("%H:%M") if match.created_at else ""
    embed.set_footer(text=f"Created {created}")
    return embed


def match_result_embed(match, winner_side: str, results: list):
    embed = discord.Embed(
        title=f"━━━ MATCH RESULT {match.display_id} ━━━",
        color=discord.Color.green() if winner_side == "CREWMATE" else discord.Color.red(),
    )
    for r in results:
        embed.add_field(
            name=f"{'👥' if r['role_side'] == 'CREWMATE' else '🔪'} {r['name']}",
            value=f"{r['elo_before']} → {r['elo_after']} ({format_elo_change(r['delta'])})",
            inline=False,
        )
    embed.set_footer(text=f"Winner: {winner_side}")
    return embed
