"""Select menus."""

import discord


class RoleSelect(discord.ui.Select):
    def __init__(self, placeholder: str = "Select a role..."):
        super().__init__(placeholder=placeholder, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()


class ChannelSelect(discord.ui.Select[discord.ui.Select["ChannelSelect"]]):
    def __init__(self, channel_types: list[discord.ChannelType] | None = None):
        super().__init__(placeholder="Select a channel...", channel_types=channel_types or [])
        self._selected_channel_id: int | None = None

    async def callback(self, interaction: discord.Interaction):
        self._selected_channel_id = int(self.values[0])
        await interaction.response.defer()
