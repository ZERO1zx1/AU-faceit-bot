"""Discord permission checking utilities."""

from typing import Any

import discord
from discord.ext import commands


def has_admin_role(ctx: commands.Context[Any], settings: dict[str, Any]) -> bool:
    if isinstance(ctx.author, discord.Member) and ctx.author.guild_permissions.administrator:
        return True
    role_id = settings.get("admin_role_id")
    if role_id and ctx.guild is not None:
        role = ctx.guild.get_role(role_id)
        if role and isinstance(ctx.author, discord.Member) and role in ctx.author.roles:
            return True
    return False


def has_moderator_role(ctx: commands.Context[Any], settings: dict[str, Any]) -> bool:
    if has_admin_role(ctx, settings):
        return True
    role_id = settings.get("moderator_role_id")
    if role_id and ctx.guild is not None:
        role = ctx.guild.get_role(role_id)
        if role and isinstance(ctx.author, discord.Member) and role in ctx.author.roles:
            return True
    return False


def has_registered_role(member: discord.Member, settings: dict[str, Any]) -> bool:
    role_id = settings.get("registered_role_id")
    if not role_id:
        return True
    role = member.guild.get_role(role_id)
    return role in member.roles if role else False


def bot_can_manage_channel(guild: discord.Guild, channel: discord.abc.GuildChannel) -> bool:
    me = guild.me
    if not me:
        return False
    perms = channel.permissions_for(me)
    return perms.manage_channels and perms.view_channel


def bot_can_manage_roles(guild: discord.Guild) -> bool:
    me = guild.me
    if not me:
        return False
    return me.guild_permissions.manage_roles
