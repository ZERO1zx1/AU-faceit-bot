"""Permission service."""

from typing import Any

import discord
from discord.ext import commands

from app.repositories.guild_repository import GuildRepository
from supabase import AsyncClient


class PermissionService:
    def __init__(self, client: AsyncClient) -> None:
        self.guilds = GuildRepository(client)

    async def is_admin_member(self, member: discord.Member) -> bool:
        """Admin check for a ``discord.Member`` (slash commands, views, modals)."""
        if member.guild_permissions.administrator or member.guild_permissions.manage_guild:
            return True
        settings = await self.guilds.get_settings(member.guild.id)
        if settings and settings.admin_role_id:
            role = member.guild.get_role(settings.admin_role_id)
            if role and role in member.roles:
                return True
        return False

    async def is_moderator_member(self, member: discord.Member) -> bool:
        """Moderator check: administration power OR the configured moderator role."""
        if await self.is_admin_member(member):
            return True
        settings = await self.guilds.get_settings(member.guild.id)
        if settings and settings.moderator_role_id:
            role = member.guild.get_role(settings.moderator_role_id)
            if role and role in member.roles:
                return True
        return False

    async def is_registered_member(self, member: discord.Member) -> bool:
        settings = await self.guilds.get_settings(member.guild.id)
        if not settings or not settings.registered_role_id:
            return True
        role = member.guild.get_role(settings.registered_role_id)
        return role in member.roles if role else False

    async def is_admin(self, ctx: commands.Context[Any]) -> bool:
        if isinstance(ctx.author, discord.Member) and ctx.author.guild_permissions.administrator:
            return True
        if ctx.guild is None:
            return False
        settings = await self.guilds.get_settings(ctx.guild.id)
        if settings and settings.admin_role_id:
            role = ctx.guild.get_role(settings.admin_role_id)
            if role and isinstance(ctx.author, discord.Member) and role in ctx.author.roles:
                return True
        return False

    async def is_moderator(self, ctx: commands.Context[Any]) -> bool:
        if await self.is_admin(ctx):
            return True
        if ctx.guild is None:
            return False
        settings = await self.guilds.get_settings(ctx.guild.id)
        if settings and settings.moderator_role_id:
            role = ctx.guild.get_role(settings.moderator_role_id)
            if role and isinstance(ctx.author, discord.Member) and role in ctx.author.roles:
                return True
        return False

    async def is_registered(self, member: discord.Member) -> bool:
        settings = await self.guilds.get_settings(member.guild.id)
        if not settings or not settings.registered_role_id:
            return True
        role = member.guild.get_role(settings.registered_role_id)
        return role in member.roles if role else False
