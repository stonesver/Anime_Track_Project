"""URL utilities for yuc-scraper."""

from typing import Optional

from yuc_scraper.config import make_season_compact, parse_season_from_compact


def build_season_url(base_url: str, season: str) -> str:
    """Build season page URL from season string (YYYY-MM or YYYYMM)."""
    compact = make_season_compact(season)
    return f"{base_url}/{compact}/"


def resolve_url(href: str, base_url: Optional[str] = None) -> str:
    """Convert relative URL to absolute URL."""
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if base_url and href.startswith("/"):
        return f"{base_url}{href}"
    if base_url:
        return f"{base_url}/{href.lstrip('/')}"
    return href


def normalize_season_input(season: str) -> str:
    """Normalize season input to YYYY-MM format.

    Accepts: current, YYYY-MM, YYYYMM
    Returns: YYYY-MM
    """
    season = season.strip()
    if season == "current":
        return "current"

    # Remove common separators
    cleaned = season.replace("-", "").replace("年", "").replace("月", "")

    if len(cleaned) == 6 and cleaned.isdigit():
        return parse_season_from_compact(cleaned)

    if len(cleaned) == 4 and cleaned.isdigit():
        # Just year, not valid
        raise ValueError(f"Invalid season format: {season}")

    raise ValueError(f"Invalid season format: {season}")


def is_valid_weekday(weekday: Optional[int]) -> bool:
    """Check if weekday is valid (1-7 or None)."""
    if weekday is None:
        return True
    return isinstance(weekday, int) and 1 <= weekday <= 7