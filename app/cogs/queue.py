"""Queue cog — handles queue join/leave via buttons and 15/15 matchmaking."""


from discord.ext import commands

from app.db import SessionFactory
from app.services.queue_service import QueueService
from app.ui.embeds import queue_embed


class QueueCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="queue-status")
    async def queue_status(self, ctx: commands.Context):
        async with SessionFactory() as session:
            svc = QueueService(session, queue_size=15)
            count = await svc.count(ctx.guild.id)
            entries = await svc.get_entries(ctx.guild.id)
            avg_elo = 0
            if entries:
                from sqlalchemy import select

                from app.models.player import Player
                elo_sum = 0
                for e in entries:
                    res = await session.execute(select(Player).where(Player.id == e.player_id))
                    p = res.scalar_one_or_none()
                    if p:
                        elo_sum += p.elo
                avg_elo = elo_sum // len(entries)
        embed = queue_embed(count=count, max_size=15, avg_elo=avg_elo)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(QueueCog(bot))
