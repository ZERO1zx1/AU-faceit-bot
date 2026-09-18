"""Select menus."""

import discord


class RoleSelect(discord.ui.Select[discord.ui.View]):
    def __init__(self, placeholder: str = "Select a role...") -> None:
        super().__init__(placeholder=placeholder, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()


class ChannelSelect(discord.ui.ChannelSelect[discord.ui.View]):
    def __init__(self, channel_types: list[discord.ChannelType] | None = None) -> None:
        super().__init__(placeholder="Select a channel...", channel_types=channel_types or [])
        self._selected_channel_id: int | None = None

    async def callback(self, interaction: discord.Interaction) -> None:
        self._selected_channel_id = self.values[0].id
        await interaction.response.defer()
