"""Result cog — /result, /result-revert."""

from discord.ext import commands

from app.repositories.player_repository import PlayerRepository
from app.services.result_service import ResultService
from app.supabase_client import get_client
from app.ui.views import ResultApprovalView


class ResultCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="result")
    @commands.has_permissions(manage_guild=True)
    async def result(self, ctx: commands.Context, match_id: int):
        client = get_client()
        svc = ResultService(client)
        match = await svc.match_repo.get(match_id)
        if not match:
            return await ctx.send("Match not found.")
        if match.result_processed:
            return await ctx.send("Result already processed.")

        players = await svc.match_repo.get_players(match_id)
        results = []
        player_repo = PlayerRepository(client)
        for mp in players:
            p = await player_repo.get_by_id(mp.player_id)
            results.append({
                "name": p.among_us_name if p else str(mp.player_id),
                "role_side": mp.role_side or "Unknown",
                "elo_before": mp.elo_before or 0,
                "elo_after": mp.elo_after or mp.elo_before or 0,
                "delta": mp.elo_delta or 0,
            })

        from app.ui.embeds import match_result_embed
        embed = match_result_embed(match, match.winner_side or "CREWMATE", results)
        view = ResultApprovalView(match_id)
        await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(ResultCog(bot))
