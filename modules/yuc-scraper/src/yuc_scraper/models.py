"""Data models for yuc-scraper."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class YucSeasonLink(BaseModel):
    """Season link from home page."""
    season: str  # YYYY-MM
    season_compact: str  # YYYYMM
    url: str
    text: str
    is_new: bool = False


class YucPlatformLink(BaseModel):
    """Platform link from weekly record."""
    url: Optional[str] = None
    label: Optional[str] = None
    region: Optional[str] = None
    kind: str = "streaming"


class YucWeeklySourceRecord(BaseModel):
    """Weekly schedule source record from yuc."""
    season: str
    weekday: Optional[int] = None
    weekday_label: Optional[str] = None
    air_time: Optional[str] = None
    start_date: Optional[str] = None
    note: Optional[str] = None
    title_text: Optional[str] = None
    title_cn: Optional[str] = None
    cover_url: Optional[str] = None
    platform_links: List[YucPlatformLink] = Field(default_factory=list)
    source_url: str = ""
    selector_hits: Dict[str, int] = Field(default_factory=dict)


class YucDetailSourceRecord(BaseModel):
    """Detail source record from yuc season page."""
    season: str
    title_text: Optional[str] = None
    title_cn: Optional[str] = None
    title_jp: Optional[str] = None
    types: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    staff: List[str] = Field(default_factory=list)
    cast: List[str] = Field(default_factory=list)
    official_url: Optional[str] = None
    broadcast_text: Optional[str] = None
    source_url: str = ""
    selector_hits: Dict[str, int] = Field(default_factory=dict)


class Diagnostic(BaseModel):
    """Diagnostic information for debugging."""
    code: str
    field: Optional[str] = None
    message: str
    raw_value: Optional[Any] = None
    severity: str = "info"


class YucSeasonPageParse(BaseModel):
    """Season page parse result."""
    season: str
    source_url: str
    weekly_records: List[YucWeeklySourceRecord] = Field(default_factory=list)
    detail_records: List[YucDetailSourceRecord] = Field(default_factory=list)
    diagnostics: List[Diagnostic] = Field(default_factory=list)


class YucFetchResult(BaseModel):
    """Result from HTTP fetch."""
    ok: bool
    content: Optional[str] = None
    status_code: Optional[int] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    source_url: str = ""


class YucParseResult(BaseModel):
    """Result wrapper for yuc scraper operations."""
    ok: bool
    source: str = "yuc"
    operation: str
    data: Optional[Any] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    diagnostics: List[Diagnostic] = Field(default_factory=list)
    freshness: Optional[str] = "live"

    def model_dump(self, **kwargs) -> dict:
        """Dump to dictionary."""
        result = {
            "ok": self.ok,
            "source": self.source,
            "operation": self.operation,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "diagnostics": [d.model_dump() if hasattr(d, "model_dump") else d for d in self.diagnostics],
            "freshness": self.freshness,
        }
        if self.data is not None:
            if hasattr(self.data, "model_dump"):
                result["data"] = self.data.model_dump()
            else:
                result["data"] = self.data
        return result