import discord
from discord.ext import commands
from database import db

class QueueCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.has_permissions(administrator=True)
    @commands.command(name="setup-queue")
    async def setup_queue(self, ctx):
        settings = await db.get_guild_settings(ctx.guild.id)
        if not settings: return await ctx.send("Run !setup-server first.")
        
        embed = discord.Embed(title="QUEUE SYSTEM", description="**0/15** players in queue.", color=discord.Color.green())
        view = QueueView(self.bot, ctx.guild.id)
        msg = await ctx.send(embed=embed, view=view)
        
        await db.upsert_queue(ctx.guild.id, msg.id, "open")
        panels = settings.get("panel_messages", {})
        panels["queue"] = msg.id
        await db.upsert_guild_settings({"guild_id": ctx.guild.id, "panel_messages": panels})
        await ctx.send("✅ Queue panel created!")

class QueueView(discord.ui.View):
    def __init__(self, bot, guild_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.guild_id = guild_id

    async def refresh(self, interaction):
        members = await db.get_queue_members(self.guild_id)
        embed = discord.Embed(title="QUEUE SYSTEM", description=f"**{len(members)}/15** players in queue.", color=discord.Color.green())
        if members:
            names = []
            for m in members:
                p = await db.get_player(self.guild_id, m["discord_user_id"])
                names.append(p["among_us_name"] if p else "Unknown")
            embed.add_field(name="Players", value="\n".join(names), inline=False)
        
        settings = await db.get_guild_settings(self.guild_id)
        msg_id = settings.get("panel_messages", {}).get("queue")
        if msg_id:
            try:
                msg = await interaction.channel.fetch_message(msg_id)
                await msg.edit(embed=embed)
            except: pass

    @discord.ui.button(label="ENTER MATCH", style=discord.ButtonStyle.success, custom_id="q_join")
    async def join(self, interaction, button):
        player = await db.get_player(self.guild_id, interaction.user.id)
        if not player or not player.get("verified"):
            return await interaction.response.send_message("Та бүртгүүлээгүй байна!", ephemeral=True)
        
        q = await db.get_queue(self.guild_id)
        if q and q.get("status") == "locked":
            return await interaction.response.send_message("Queue locked!", ephemeral=True)
        
        try: await db.add_queue_member(self.guild_id, interaction.user.id)
        except: return await interaction.response.send_message("Та аль хэдийн queue-д байна!", ephemeral=True)
        
        await interaction.response.send_message("Queue-д орлоо!", ephemeral=True)
        await self.refresh(interaction)
        
        members = await db.get_queue_members(self.guild_id)
        if len(members) >= 15:
            await self.trigger_match(interaction, members)

    @discord.ui.button(label="LEAVE MATCH", style=discord.ButtonStyle.danger, custom_id="q_leave")
    async def leave(self, interaction, button):
        await db.remove_queue_member(self.guild_id, interaction.user.id)
        await interaction.response.send_message("Queue-с гарлаа.", ephemeral=True)
        await self.refresh(interaction)

    async def trigger_match(self, interaction, members):
        await db.upsert_queue(self.guild_id, status="locked")
        uids = [m["discord_user_id"] for m in members]
        match = await db.create_match(self.guild_id, uids)
        
        settings = await db.get_guild_settings(self.guild_id)
        cat = interaction.guild.get_channel(settings.get("match_category_id"))
        
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True)
        }
        for uid in uids:
            m = interaction.guild.get_member(uid)
            if m: overwrites[m] = discord.PermissionOverwrite(view_channel=True, send_messages=True, connect=True)
        
        t_ch = await cat.create_text_channel(f"match-{match['match_id'][:8]}", overwrites=overwrites)
        v_ch = await cat.create_voice_channel(f"match-{match['match_id'][:8]}", overwrites=overwrites)
        await db.update_match_channels(match['match_id'], t_ch.id, v_ch.id)
        
        await t_ch.send(f"**Match {match['match_id'][:8]}**\nAdmin: `!result {match['match_id']} ...`")
        await db.clear_queue(self.guild_id)
        await db.upsert_queue(self.guild_id, status="open")
        await self.refresh(interaction)
        await interaction.channel.send(f"✅ Match {match['match_id'][:8]} created!")

async def setup(bot):
    await bot.add_cog(QueueCog(bot))
