"""Normalizers for anime data fields."""

import re
import unicodedata
from typing import Any, Dict, List, Optional, Pattern, Tuple, Union

from anime_parser.errors import (
    create_diagnostic,
    invalid_date_diag,
    invalid_season_diag,
    invalid_time_diag,
    invalid_url_diag,
    invalid_weekday_diag,
)
from anime_parser.models import Diagnostic, NormalizedValue, PlatformLink

# Season month mapping
VALID_SEASON_MONTHS = {"01", "04", "07", "10"}

# Weekday patterns
WEEKDAY_PATTERNS: List[Tuple[Pattern, Optional[int]]] = [
    # Chinese weekday (周一 - 周日)
    (re.compile(r"^周([一二三四五六日])"), None),
    # Chinese weekday (星期一 - 星期日)
    (re.compile(r"^星期([一二三四五六日])"), None),
    # Japanese weekday (月火水木金土日)
    (re.compile(r"^[月火水木金土日]$"), None),
    # English abbreviated (mon, tue, wed, thu, fri, sat, sun)
    (re.compile(r"^(mon|tue|wed|thu|fri|sat|sun)$", re.I), None),
]

WEEKDAY_MAP = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7,
    "月": 1, "火": 2, "水": 3, "木": 4, "金": 5, "土": 6,
    "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7,
}

NO_FIXED_WEEKDAY_VALUES = {"网络放送", "其他", "未定", "待定", ""}


def normalize_season(value: Optional[str]) -> NormalizedValue[str]:
    """Normalize season string to YYYY-MM format."""
    if value is None:
        return NormalizedValue(None, invalid_season_diag(None, "Season is required but missing"))

    # Remove whitespace
    value = value.strip()

    # Try YYYYMM format
    m = re.match(r"^(\d{4})(\d{2})$", value)
    if m:
        year, month = m.groups()
        if month in VALID_SEASON_MONTHS:
            return NormalizedValue(f"{year}-{month}")
        else:
            return NormalizedValue(None, invalid_season_diag(value, f"Invalid season month: {month}"))

    # Try YYYY-MM format
    m = re.match(r"^(\d{4})-(\d{2})$", value)
    if m:
        year, month = m.groups()
        if month in VALID_SEASON_MONTHS:
            return NormalizedValue(f"{year}-{month}")
        else:
            return NormalizedValue(None, invalid_season_diag(value, f"Invalid season month: {month}"))

    # Try YYYY年M月 or YYYY年MM月 format
    m = re.match(r"^(\d{4})年(\d{1,2})月$", value)
    if m:
        year, month = m.groups()
        month_padded = month.zfill(2)
        if month_padded in VALID_SEASON_MONTHS:
            return NormalizedValue(f"{year}-{month_padded}")
        else:
            return NormalizedValue(None, invalid_season_diag(value, f"Invalid season month: {month}"))

    return NormalizedValue(None, invalid_season_diag(value, "Cannot parse season format"))


def normalize_weekday(value: Optional[Union[str, int]]) -> NormalizedValue[Optional[int]]:
    """Normalize weekday to integer 1-7 (1=Monday, 7=Sunday)."""
    if value is None:
        return NormalizedValue(None)

    # If already integer 1-7, validate
    if isinstance(value, int):
        if 1 <= value <= 7:
            return NormalizedValue(value)
        else:
            return NormalizedValue(None, invalid_weekday_diag(value, f"Invalid weekday value: {value}"))

    # Convert to string and strip
    value = str(value).strip()

    # Check for no-fixed weekday values
    if value in NO_FIXED_WEEKDAY_VALUES:
        return NormalizedValue(None)

    # Direct numeric string
    if value.isdigit():
        num = int(value)
        if 1 <= num <= 7:
            return NormalizedValue(num)
        else:
            return NormalizedValue(None, invalid_weekday_diag(value, f"Invalid weekday: {value}"))

    # Try pattern matching
    for pattern, _ in WEEKDAY_PATTERNS:
        m = pattern.match(value)
        if m:
            if m.lastindex and m.lastindex >= 1:
                key = m.group(1).lower()  # Normalize to lowercase for lookup
            else:
                key = value.lower()
            weekday = WEEKDAY_MAP.get(key)
            if weekday is not None:
                return NormalizedValue(weekday)

    return NormalizedValue(None, invalid_weekday_diag(value, f"Cannot normalize weekday: {value}"))


def normalize_air_time(value: Optional[str]) -> NormalizedValue[Optional[str]]:
    """Normalize air time to HH:mm format."""
    if value is None:
        return NormalizedValue(None)

    value = value.strip()

    # Check for special values
    if value in {"年番", "待定", ""}:
        return NormalizedValue(None, invalid_time_diag(value, "Air time is not fixed"))

    # Remove trailing ~
    value = value.rstrip("~")

    # Extract time pattern H:mm or HH:mm
    m = re.search(r"(\d{1,2}):(\d{2})", value)
    if m:
        hour = int(m.group(1))
        minute = m.group(2)
        # Pad single digit hour
        hour_str = str(hour).zfill(2)
        return NormalizedValue(f"{hour_str}:{minute}")

    return NormalizedValue(None, invalid_time_diag(value, f"Cannot parse air time: {value}"))


def normalize_start_date(value: Optional[str], season: Optional[str]) -> NormalizedValue[Optional[str]]:
    """Normalize start date to YYYY-MM-DD format."""
    if value is None:
        return NormalizedValue(None)

    value = value.strip().rstrip("~")

    if not value:
        return NormalizedValue(None)

    # Extract year from season
    year = None
    if season:
        m = re.match(r"(\d{4})-\d{2}", season)
        if m:
            year = m.group(1)

    # Try YYYY-MM-DD format
    if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        return NormalizedValue(value)

    # Try MM/DD format
    m = re.match(r"^(\d{1,2})/(\d{1,2})$", value)
    if m:
        month = m.group(1).zfill(2)
        day = m.group(2).zfill(2)
        if year:
            return NormalizedValue(f"{year}-{month}-{day}")
        else:
            return NormalizedValue(None, invalid_date_diag(value, "Cannot determine year for date"))

    # Try M/D format
    m = re.match(r"^(\d)/(\d)$", value)
    if m:
        month = m.group(1).zfill(2)
        day = m.group(2).zfill(2)
        if year:
            return NormalizedValue(f"{year}-{month}-{day}")
        else:
            return NormalizedValue(None, invalid_date_diag(value, "Cannot determine year for date"))

    return NormalizedValue(None, invalid_date_diag(value, f"Cannot parse date format: {value}"))


def clean_display_text(value: Optional[str]) -> Optional[str]:
    """Clean text for display by removing HTML and normalizing whitespace."""
    if value is None:
        return None

    # Replace <br> with space
    value = re.sub(r"<br\s*/?>", " ", value, flags=re.IGNORECASE)

    # Collapse multiple spaces
    value = re.sub(r"\s+", " ", value)

    # Strip leading/trailing whitespace
    value = value.strip()

    return value if value else None


def normalize_title_for_match(value: Optional[str]) -> str:
    """Normalize title for matching using NFKC and lowercasing."""
    if value is None:
        return ""

    # NFKC normalization
    value = unicodedata.normalize("NFKC", value)

    # Lowercase
    value = value.lower()

    # Remove all whitespace
    value = re.sub(r"\s+", "", value)

    # Simplify common punctuation differences
    # Remove dotted separators used in numbering like "1. " -> ""
    value = re.sub(r"[.．・]+", "", value)

    # Remove HTML tags
    value = re.sub(r"<[^>]+>", "", value)

    return value


def normalize_url(value: Optional[str], base_url: Optional[str] = None) -> NormalizedValue[Optional[str]]:
    """Normalize URL, handling relative URLs and validating protocol."""
    if value is None:
        return NormalizedValue(None)

    value = value.strip()

    if not value:
        return NormalizedValue(None)

    # Check protocol
    if re.match(r"^https?://", value):
        return NormalizedValue(value)

    # Handle relative URL with base
    if base_url and not re.match(r"^https?://", value):
        # Simple relative path handling
        if value.startswith("/"):
            # Extract scheme and host from base_url
            m = re.match(r"^(https?://[^/]+)", base_url)
            if m:
                return NormalizedValue(m.group(1) + value)
        else:
            # Relative to current path
            return NormalizedValue(value)

    # Non-HTTP protocol
    if re.match(r"^[a-z]+://", value):
        return NormalizedValue(None, invalid_url_diag(value, "Only HTTP/HTTPS URLs are supported"))

    return NormalizedValue(None, invalid_url_diag(value, "Invalid URL format"))


def normalize_platform_link(raw: Dict[str, Any]) -> PlatformLink:
    """Normalize a source platform link to standard PlatformLink."""
    return PlatformLink(
        url=raw.get("url"),
        label=raw.get("label"),
        region=raw.get("region"),
        kind=raw.get("kind"),
    )