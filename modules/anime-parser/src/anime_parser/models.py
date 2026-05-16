"""Data models for anime parser."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


class SourcePlatformLink(BaseModel):
    """Platform link from source record."""

    url: str | None = None
    label: str | None = None
    region: str | None = None
    kind: str | None = None


class PlatformLink(BaseModel):
    """Normalized platform link."""

    url: str | None = None
    label: str | None = None
    region: str | None = None
    kind: str | None = None


class SourceAnimeRecord(BaseModel):
    """Source anime record from data source adapter."""

    source: str
    source_url: str | None = None
    source_id: str | None = None
    season_raw: str | None = None
    title_raw: str | None = None
    title_cn_raw: str | None = None
    title_jp_raw: str | None = None
    title_en_raw: str | None = None
    aliases_raw: list[str] = Field(default_factory=list)
    weekday_raw: str | int | None = None
    air_time_raw: str | None = None
    start_date_raw: str | None = None
    description_raw: str | None = None
    cover_url_raw: str | None = None
    official_url_raw: str | None = None
    platform_links_raw: list[SourcePlatformLink] = Field(default_factory=list)
    source_payload: dict[str, Any] = Field(default_factory=dict)


class AnimeItem(BaseModel):
    """Normalized anime item."""

    source: str
    external_id: str | None = None
    external_url: str | None = None
    season: str | None = None
    title_cn: str | None = None
    title_jp: str | None = None
    title_en: str | None = None
    aliases: list[str] = Field(default_factory=list)
    weekday: int | None = None
    air_time: str | None = None
    start_date: str | None = None
    timezone: str = "Asia/Shanghai"
    description: str | None = None
    cover_url: str | None = None
    official_url: str | None = None
    platform_links: list[PlatformLink] = Field(default_factory=list)
    confidence: float = 1.0


class ScheduleDay(BaseModel):
    """Schedule day containing anime items."""

    weekday: int
    label: str
    items: list[AnimeItem] = Field(default_factory=list)


class WeeklySchedule(BaseModel):
    """Weekly schedule organized by season."""

    source: str
    season: str
    days: list[ScheduleDay] = Field(default_factory=list)


class Diagnostic(BaseModel):
    """Diagnostic information for debugging."""

    code: str
    field: str | None = None
    message: str
    raw_value: Any | None = None
    severity: str = "info"


T = TypeVar("T")


class NormalizedValue(Generic[T]):
    """Wrapper for normalized value with diagnostic."""

    def __init__(self, value: T | None, diagnostic: Diagnostic | None = None):
        self.value = value
        self.diagnostic = diagnostic

    @property
    def ok(self) -> bool:
        return self.diagnostic is None


class AnimeParseResult(BaseModel):
    """Result wrapper for all parser operations."""

    ok: bool
    source: str | None = None
    operation: str
    data: Any | None = None
    error_type: str | None = None
    error_message: str | None = None
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    freshness: str | None = "live"