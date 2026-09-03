import discord
from discord.ext import commands
from database import db
from utils.logger import log_to_discord

class SetupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.has_permissions(administrator=True)
    @commands.command(name="setup-server")
    async def setup_server(self, ctx):
        guild = ctx.guild
        unverified = await guild.create_role(name="Unverified")
        verified = await guild.create_role(name="Verified")
        cat = await guild.create_category(name="AU Matches")
        log_ch = await guild.create_text_channel("bot-logs")
        reg_ch = await guild.create_text_channel("register")
        
        data = {
            "guild_id": guild.id, "unverified_role_id": unverified.id, "verified_role_id": verified.id,
            "match_category_id": cat.id, "log_channel_id": log_ch.id, "register_channel_id": reg_ch.id
        }
        await db.upsert_guild_settings(data)
        await ctx.send("✅ Server setup complete!")

    @commands.has_permissions(administrator=True)
    @commands.command(name="setup-register")
    async def setup_register(self, ctx):
        settings = await db.get_guild_settings(ctx.guild.id)
        if not settings: return await ctx.send("Run !setup-server first.")
        
        embed = discord.Embed(
            title="AMONG US MONGOLIA",
            description="**FACEIT БҮРТГЭЛ**\n\nТоглолтод оролцохын тулд эхлээд бүртгүүлнэ үү.\nДоорх товчийг дарж Among Us нэрээ бүртгүүлээрэй.",
            color=discord.Color.blue()
        )
        view = RegisterView(self.bot, ctx.guild.id)
        msg = await ctx.send(embed=embed, view=view)
        
        panels = settings.get("panel_messages", {})
        panels["register"] = msg.id
        await db.upsert_guild_settings({"guild_id": ctx.guild.id, "panel_messages": panels})
        await ctx.send("✅ Registration panel created!")

    @commands.has_permissions(administrator=True)
    @commands.command(name="setup-faceit-level")
    async def setup_levels(self, ctx):
        guild = ctx.guild
        settings = await db.get_guild_settings(guild.id)
        level_roles = {}
        for i in range(1, 11):
            role = discord.utils.get(guild.roles, name=f"Level {i}") or await guild.create_role(name=f"Level {i}")
            level_roles[str(i)] = role.id
        await db.upsert_guild_settings({"guild_id": guild.id, "level_role_ids": level_roles})
        await ctx.send("✅ Level roles (1-10) configured!")

class RegisterView(discord.ui.View):
    def __init__(self, bot, guild_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.guild_id = guild_id

    @discord.ui.button(label="БҮРТГҮҮЛЭХ", style=discord.ButtonStyle.primary, custom_id="reg_btn")
    async def register(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = await db.get_player(self.guild_id, interaction.user.id)
        if player and player.get("verified"):
            return await interaction.response.send_message("Та аль хэдийн бүртгүүлсэн байна!", ephemeral=True)
        await interaction.response.send_modal(RegisterModal(self.bot, self.guild_id))

class RegisterModal(discord.ui.Modal, title="Among Us Бүртгэл"):
    username = discord.ui.TextInput(label="Among Us Username", placeholder="Нэрээ оруулна уу...", required=True)
    def __init__(self, bot, guild_id):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        name = self.username.value.strip()
        await db.create_player(self.guild_id, interaction.user.id, name)
        settings = await db.get_guild_settings(self.guild_id)
        unv = interaction.guild.get_role(settings.get("unverified_role_id"))
        ver = interaction.guild.get_role(settings.get("verified_role_id"))
        if unv: await interaction.user.remove_roles(unv)
        if ver: await interaction.user.add_roles(ver)
        try: await interaction.user.edit(nick=name)
        except: pass
        await db.log_audit(self.guild_id, "REGISTER", interaction.user.id, target=name)
        await interaction.response.send_message(f"Амжилттай бүртгүүллээ! {name}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(SetupCog(bot))
