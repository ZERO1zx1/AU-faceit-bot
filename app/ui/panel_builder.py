"""Centralized Discord embed builder and validator for custom panels.

The API enforces the Discord embed limits so every panel produced by the bot is
guaranteed to be a valid embed regardless of which command created it:

- title:            256 characters
- description:      4096 characters
- footer text:      2048 characters
- field name:       256 characters, field value: 1024 characters, 25 fields max
- total embed size: 6000 characters
- color:            0 .. 0xFFFFFF
- thumbnail/image:  http(s) URL (or None)
"""

from __future__ import annotations

import re

import discord

_TITLE_MAX = 256
_DESCRIPTION_MAX = 4096
_FOOTER_MAX = 2048
_FIELD_NAME_MAX = 256
_FIELD_VALUE_MAX = 1024
_MAX_FIELDS = 25
_TOTAL_MAX = 6000

_URL_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)
_CUSTOM_EMOJI_RE = re.compile(r"^<a?:\w+:\d{15,20}>$")


class EmbedValidationError(ValueError):
    """Raised when a panel definition exceeds Discord embed limits."""


def _check(value: str | None, limit: int, label: str) -> str | None:
    if value is None:
        return None
    if len(value) > limit:
        raise EmbedValidationError(
            f"{label} хэт урт байна ({len(value)}/{limit} тэмдэгт)."
        )
    return value


def _check_color(color: int | None) -> int | None:
    if color is None:
        return None
    if not isinstance(color, int) or isinstance(color, bool):
        raise EmbedValidationError("Color нь бүхэл тоо байх ёстой.")
    if not 0 <= color <= 0xFFFFFF:
        raise EmbedValidationError(f"Color 0x000000–0xFFFFFF хооронд байх ёстой (өгсөн: {color}).")
    return color


def _check_url(url: str | None, label: str) -> str | None:
    if url is None:
        return None
    if not _URL_RE.match(url):
        raise EmbedValidationError(f"{label} нь зөв http(s) URL байх ёстой.")
    return url


def _check_emoji(emoji: str | None) -> str | None:
    if emoji is None:
        return None
    emoji = emoji.strip()
    if not emoji:
        return None
    if _CUSTOM_EMOJI_RE.match(emoji):
        return emoji
    # A single unicode grapheme (common emoji / letter).
    if len(emoji) <= 8:
        return emoji
    raise EmbedValidationError("Emoji нэг тэмдэгт эсвэл Discord custom emoji байх ёстой.")


class PanelEmbedBuilder:
    """Builds and validates an embed from a ``Panel`` (or plain fields dict)."""

    def __init__(
        self,
        *,
        title: str | None = None,
        description: str | None = None,
        color: int | None = None,
        thumbnail_url: str | None = None,
        image_url: str | None = None,
        footer: str | None = None,
    ) -> None:
        self.title = _check(title, _TITLE_MAX, "Title")
        self.description = _check(description, _DESCRIPTION_MAX, "Description")
        self.color = _check_color(color)
        self.thumbnail_url = _check_url(thumbnail_url, "Thumbnail URL")
        self.image_url = _check_url(image_url, "Image URL")
        self.footer = _check(footer, _FOOTER_MAX, "Footer")
        self._fields: list[dict] = []

    @classmethod
    def from_panel(cls, panel) -> PanelEmbedBuilder:
        color = panel.color if panel.color is not None else None
        return cls(
            title=panel.title,
            description=panel.description,
            color=color,
            thumbnail_url=panel.thumbnail_url,
            image_url=panel.image_url,
            footer=panel.footer,
        )

    def build(self) -> discord.Embed:
        embed = discord.Embed(
            title=self.title or discord.Embed.Empty,
            description=self.description or discord.Embed.Empty,
            color=self.color or discord.Colour.blurple(),
        )
        if self.thumbnail_url:
            embed.set_thumbnail(url=self.thumbnail_url)
        if self.image_url:
            embed.set_image(url=self.image_url)
        if self.footer:
            embed.set_footer(text=self.footer)
        return embed

    def add_field(self, name: str, value: str, *, inline: bool = False) -> None:
        if self._field_count() >= _MAX_FIELDS:
            raise EmbedValidationError(f"Embed {_MAX_FIELDS} field-ээс их байж болохгүй.")
        _check(name, _FIELD_NAME_MAX, "Field name")
        _check(value, _FIELD_VALUE_MAX, "Field value")
        self._fields.append({"name": name, "value": value, "inline": inline})

    def _field_count(self) -> int:
        return len(self._fields)

    def total_size(self) -> int:
        size = len(self.title or "") + len(self.description or "") + len(self.footer or "")
        for field in self._fields:
            size += len(field["name"]) + len(field["value"])
        if size > _TOTAL_MAX:
            raise EmbedValidationError(f"Embed нь {_TOTAL_MAX} тэмдэгтээс хэтэрсэн ({size}).")
        return size

    def validate(self) -> None:
        """Raise ``EmbedValidationError`` if any embed limit is exceeded."""
        self.total_size()


def validate_emoji(emoji: str | None) -> str | None:
    """Return a validated emoji or ``None`` for user-supplied button/select emoji."""
    return _check_emoji(emoji)


def parse_color(value: str | int) -> int | None:
    """Parse a color from hex (``#RRGGBB`` / ``0xRRGGBB``) or an int."""
    if isinstance(value, int):
        return _check_color(value)
    text = str(value).strip().lstrip("#").replace("0x", "").replace("0X", "")
    try:
        return _check_color(int(text, 16))
    except ValueError as exc:
        raise EmbedValidationError(f"Color-г танихгүй байна: {value!r}") from exc
