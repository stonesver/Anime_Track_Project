"""yuc-scraper: Static HTML scraper for yuc.wiki."""

from yuc_scraper.config import DEFAULT_CONFIG, YucScrapeConfig
from yuc_scraper.errors import ErrorType
from yuc_scraper.models import (
    Diagnostic,
    YucFetchResult,
    YucParseResult,
    YucSeasonLink,
    YucSeasonPageParse,
)

__all__ = [
    "DEFAULT_CONFIG",
    "Diagnostic",
    "ErrorType",
    "YucFetchResult",
    "YucParseResult",
    "YucScrapeConfig",
    "YucSeasonLink",
    "YucSeasonPageParse",
]