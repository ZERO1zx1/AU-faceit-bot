"""Pydantic base models shared across the data layer."""

from __future__ import annotations

from datetime import datetime
from typing import TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T", bound="SupabaseModel")


class SupabaseModel(BaseModel):
    """Base model for all Supabase-backed entities.

    Provides helpers to construct instances from PostgREST rows (dicts) and to
    serialize back to plain dicts for REST insert/update payloads.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @classmethod
    def from_row(cls: type[T], row: dict) -> T:
        """Build a model from a PostgREST row dict."""
        return cls.model_validate(row)

    def to_payload(self) -> dict:
        """Return a plain dict suitable for a REST insert/update payload.

        ``None`` values are dropped so that partial updates do not clear
        columns that were not meant to change.
        """
        payload = self.model_dump(exclude_none=False)
        payload.pop("id", None)
        return payload


class TimestampedModel(SupabaseModel):
    """Adds created_at/updated_at fields used across several tables."""

    created_at: datetime | None = None
    updated_at: datetime | None = None
