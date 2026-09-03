"""Queue cog — handles queue join/leave via buttons and 15/15 matchmaking."""


from discord.ext import commands

from app.repositories.player_repository import PlayerRepository
from app.services.queue_service import QueueService
from app.supabase_client import get_client
from app.ui.embeds import queue_embed


class QueueCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="queue-status")
    async def queue_status(self, ctx: commands.Context):
        client = get_client()
        svc = QueueService(client, queue_size=15)
        count = await svc.count(ctx.guild.id)
        entries = await svc.get_entries(ctx.guild.id)
        avg_elo = 0
        if entries:
            players = PlayerRepository(client)
            elo_sum = 0
            for e in entries:
                p = await players.get_by_id(e.player_id)
                if p:
                    elo_sum += p.elo
            avg_elo = elo_sum // len(entries)
        embed = queue_embed(count=count, max_size=15, avg_elo=avg_elo)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(QueueCog(bot))
