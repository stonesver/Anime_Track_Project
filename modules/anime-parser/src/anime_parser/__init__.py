"""Anime parser - parsing and normalization module for anime data."""

from anime_parser.models import (
    AnimeItem,
    AnimeParseResult,
    PlatformLink,
    ScheduleDay,
    SourceAnimeRecord,
    WeeklySchedule,
)
from anime_parser.errors import Diagnostic
from anime_parser.service import normalize_anime, normalize_weekly_schedule
from anime_parser.search import search_anime_items
from anime_parser.merge import merge_anime_records

__all__ = [
    "AnimeItem",
    "AnimeParseResult",
    "Diagnostic",
    "PlatformLink",
    "ScheduleDay",
    "SourceAnimeRecord",
    "WeeklySchedule",
    "normalize_anime",
    "normalize_weekly_schedule",
    "search_anime_items",
    "merge_anime_records",
]