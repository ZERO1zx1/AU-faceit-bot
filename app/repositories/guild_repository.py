"""Guild repository."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guild import Guild, GuildSettings


class GuildRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_guild(self, guild_id: int) -> Guild | None:
        return await self.session.get(Guild, guild_id)

    async def ensure_guild(self, guild_id: int) -> Guild:
        guild = await self.get_guild(guild_id)
        if guild is None:
            guild = Guild(id=guild_id, enabled=True)
            self.session.add(guild)
            await self.session.flush()
        return guild

    async def get_settings(self, guild_id: int) -> GuildSettings | None:
        return await self.session.get(GuildSettings, guild_id)

    async def upsert_settings(self, guild_id: int, **kwargs) -> GuildSettings:
        await self.ensure_guild(guild_id)
        settings = await self.get_settings(guild_id)
        if settings is None:
            settings = GuildSettings(guild_id=guild_id, **kwargs)
            self.session.add(settings)
        else:
            for k, v in kwargs.items():
                setattr(settings, k, v)
        await self.session.flush()
        return settings
