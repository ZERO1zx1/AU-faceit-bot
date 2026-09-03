"""Level role model for FACEIT-style level boundaries."""


from sqlalchemy import BigInteger, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LevelRole(Base):
    __tablename__ = "level_roles"
    __table_args__ = (
        UniqueConstraint("guild_id", "level", name="uq_level_roles_guild_level"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    min_elo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_elo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    role_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
