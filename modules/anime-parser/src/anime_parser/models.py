"""Data models for anime parser."""

from typing import Any, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, Field


class SourcePlatformLink(BaseModel):
    """Platform link from source record."""

    url: Optional[str] = None
    label: Optional[str] = None
    region: Optional[str] = None
    kind: Optional[str] = None


class PlatformLink(BaseModel):
    """Normalized platform link."""

    url: Optional[str] = None
    label: Optional[str] = None
    region: Optional[str] = None
    kind: Optional[str] = None


class SourceAnimeRecord(BaseModel):
    """Source anime record from data source adapter."""

    source: str
    source_url: Optional[str] = None
    source_id: Optional[str] = None
    season_raw: Optional[str] = None
    title_raw: Optional[str] = None
    title_cn_raw: Optional[str] = None
    title_jp_raw: Optional[str] = None
    title_en_raw: Optional[str] = None
    aliases_raw: List[str] = Field(default_factory=list)
    weekday_raw: Optional[Union[str, int]] = None
    air_time_raw: Optional[str] = None
    start_date_raw: Optional[str] = None
    description_raw: Optional[str] = None
    cover_url_raw: Optional[str] = None
    official_url_raw: Optional[str] = None
    platform_links_raw: List[SourcePlatformLink] = Field(default_factory=list)
    source_payload: dict[str, Any] = Field(default_factory=dict)


class AnimeItem(BaseModel):
    """Normalized anime item."""

    source: str
    external_id: Optional[str] = None
    external_url: Optional[str] = None
    season: Optional[str] = None
    title_cn: Optional[str] = None
    title_jp: Optional[str] = None
    title_en: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    weekday: Optional[int] = None
    air_time: Optional[str] = None
    start_date: Optional[str] = None
    timezone: str = "Asia/Shanghai"
    description: Optional[str] = None
    cover_url: Optional[str] = None
    official_url: Optional[str] = None
    platform_links: List[PlatformLink] = Field(default_factory=list)
    confidence: float = 1.0


class ScheduleDay(BaseModel):
    """Schedule day containing anime items."""

    weekday: int
    label: str
    items: List[AnimeItem] = Field(default_factory=list)


class WeeklySchedule(BaseModel):
    """Weekly schedule organized by season."""

    source: str
    season: str
    days: List[ScheduleDay] = Field(default_factory=list)


class Diagnostic(BaseModel):
    """Diagnostic information for debugging."""

    code: str
    field: Optional[str] = None
    message: str
    raw_value: Optional[Any] = None
    severity: str = "info"


T = TypeVar("T")


class NormalizedValue(Generic[T]):
    """Wrapper for normalized value with diagnostic."""

    def __init__(self, value: Optional[T], diagnostic: Optional[Diagnostic] = None):
        self.value = value
        self.diagnostic = diagnostic

    @property
    def ok(self) -> bool:
        return self.diagnostic is None


class AnimeParseResult(BaseModel):
    """Result wrapper for all parser operations."""

    ok: bool
    source: Optional[str] = None
    operation: str
    data: Optional[Any] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    diagnostics: List[Diagnostic] = Field(default_factory=list)
    freshness: Optional[str] = "live"