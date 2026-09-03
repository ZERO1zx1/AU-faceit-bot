"""Permission service."""

import discord
from discord.ext import commands

from app.repositories.guild_repository import GuildRepository
from supabase import AsyncClient


class PermissionService:
    def __init__(self, client: AsyncClient) -> None:
        self.guilds = GuildRepository(client)

    async def is_admin(self, ctx: commands.Context) -> bool:
        if ctx.author.guild_permissions.administrator:
            return True
        settings = await self.guilds.get_settings(ctx.guild.id)
        if settings and settings.admin_role_id:
            role = ctx.guild.get_role(settings.admin_role_id)
            if role and role in ctx.author.roles:
                return True
        return False

    async def is_moderator(self, ctx: commands.Context) -> bool:
        if await self.is_admin(ctx):
            return True
        settings = await self.guilds.get_settings(ctx.guild.id)
        if settings and settings.moderator_role_id:
            role = ctx.guild.get_role(settings.moderator_role_id)
            if role and role in ctx.author.roles:
                return True
        return False

    async def is_registered(self, member: discord.Member) -> bool:
        settings = await self.guilds.get_settings(member.guild.id)
        if not settings or not settings.registered_role_id:
            return True
        role = member.guild.get_role(settings.registered_role_id)
        return role in member.roles if role else False
