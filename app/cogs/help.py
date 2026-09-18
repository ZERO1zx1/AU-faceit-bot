"""Help cog — /help slash command listing the real registered command tree."""

import discord
from discord import app_commands
from discord.ext import commands

ADMIN_GROUPS = {"setup", "panel", "admin"}
_ADMIN_REVIEW = "review"


def _is_admin_node(node) -> bool:
    if node.name in ADMIN_GROUPS:
        return True
    perms = getattr(node, "default_permissions", None)
    return perms is not None and (perms.administrator or perms.manage_guild or perms.manage_roles)


def _subcommands(node):
    return {
        sub.name: (sub, sub.description or "")
        for sub in node.walk_commands()
    }


def _render(node, indent: int = 1) -> str:
    if isinstance(node, app_commands.Group):
        prefix = f"{'`/' + node.name + '`'}"
        lines = [f"{'  ' * (indent - 1)}◆ **{prefix}** — {node.description or ''}"]
        for sub in node.commands:
            rendered = _render(sub, indent + 1)
            lines.append(rendered)
        return "\n".join(lines)
    prefix = "`/" + node.name + "`"
    if getattr(node, "parent", None) is not None:
        prefix = f"`/{node.parent.name} {node.name}`"
    return f"{'  ' * indent}• {prefix} — {node.description or ''}"


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="help", description="Бүх slash command-ын жагсаалтыг харах."
    )
    @app_commands.guild_only()
    async def help(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        commands_tree = interaction.client.tree.get_commands(
            guild=interaction.guild, type=discord.AppCommandType.chat_input
        )

        general_lines: list[str] = []
        admin_lines: list[str] = []

        for node in sorted(commands_tree, key=lambda c: c.name):
            if _is_admin_node(node):
                admin_lines.append(_render(node))
            else:
                if node.name == "result":
                    children = _subcommands(node)
                    for child_name, child_node in children.items():
                        lines = _render(child_node, indent=1)
                        if child_name == _ADMIN_REVIEW:
                            admin_lines.append(lines)
                        else:
                            general_lines.append(lines)
                    continue
                general_lines.append(_render(node))

        if general_lines:
            value = "\n".join(general_lines)
            if len(value) > 1024:
                value = value[:1021] + "..."
        else:
            value = "Таньд харагдах slash command байхгүй."

        embed = discord.Embed(
            title="🎮 AU FACEIT Bot — Commands",
            description="Slash command-ыг Discord дээр шууд ашиглана.",
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="👤 Player", value=value, inline=False
        )

        if admin_lines:
            admin_value = "\n".join(admin_lines)
            if len(admin_value) > 1024:
                admin_value = admin_value[:1021] + "..."
            embed.add_field(name="⚙️ Admin", value=admin_value, inline=False)

        embed.set_footer(
            text=f"Requested by {interaction.user}",
            icon_url=interaction.user.display_avatar.url,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
