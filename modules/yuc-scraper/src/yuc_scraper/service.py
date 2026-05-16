"""Service layer for yuc-scraper, orchestrating requests, parsing, and query operations."""

from functools import cmp_to_key
from typing import Any, List, Optional, Union

from yuc_scraper.client import YucHttpClient
from yuc_scraper.config import DEFAULT_CONFIG, make_season_compact, YucScrapeConfig
from yuc_scraper.errors import (
    ErrorType,
    ambiguous_match_diag,
    invalid_params_diag,
    not_found_diag,
    parse_schema_changed_diag,
    parse_zero_items_diag,
)
from yuc_scraper.models import (
    Diagnostic,
    YucFetchResult,
    YucParseResult,
    YucSeasonLink,
    YucSeasonPageParse,
)
from yuc_scraper.parser import parse_season_links, parse_season_page, select_current_season
from yuc_scraper.url import build_season_url, is_valid_weekday, normalize_season_input


class YucService:
    """Main service for yuc scraping operations."""

    def __init__(
        self,
        client: Optional[YucHttpClient] = None,
        config: YucScrapeConfig = DEFAULT_CONFIG,
    ):
        self.client = client or YucHttpClient()
        self.config = config

    def get_current_season(self) -> YucParseResult:
        """Get current season from yuc home page."""
        operation = "yuc_get_current_season"

        # Fetch home page
        fetch_result = self.client.fetch_home()
        if not fetch_result.ok:
            return YucParseResult(
                ok=False,
                operation=operation,
                error_type=fetch_result.error_type,
                error_message=fetch_result.error_message,
            )

        # Parse season links
        links, diags = parse_season_links(fetch_result.content, self.config)
        diagnostics = list(diags)

        if not links:
            return YucParseResult(
                ok=False,
                operation=operation,
                error_type=ErrorType.PARSE_SCHEMA_CHANGED,
                error_message="No valid season links found on home page",
                diagnostics=diagnostics,
            )

        # Select current season
        selected, select_diags = select_current_season(links)
        diagnostics.extend(select_diags)

        if not selected:
            return YucParseResult(
                ok=False,
                operation=operation,
                error_type=ErrorType.PARSE_ZERO_ITEMS,
                error_message="Could not determine current season",
                diagnostics=diagnostics,
            )

        return YucParseResult(
            ok=True,
            operation=operation,
            data={"season": selected.season},
            diagnostics=diagnostics,
        )

    def get_weekly_schedule(
        self,
        season: str = "current",
        weekday: Optional[int] = None,
    ) -> YucParseResult:
        """Get weekly schedule for a season, optionally filtered by weekday."""
        operation = "yuc_get_weekly_schedule"
        diagnostics = []

        # Validate weekday
        if weekday is not None and not is_valid_weekday(weekday):
            return YucParseResult(
                ok=False,
                operation=operation,
                error_type=ErrorType.INVALID_PARAMS,
                error_message="weekday must be between 1 and 7",
            )

        # Resolve season
        season_str = season
        if season == "current":
            current_result = self.get_current_season()
            if not current_result.ok:
                return current_result
            season_str = current_result.data["season"]
        else:
            try:
                season_str = normalize_season_input(season)
            except ValueError as e:
                return YucParseResult(
                    ok=False,
                    operation=operation,
                    error_type=ErrorType.INVALID_PARAMS,
                    error_message=str(e),
                )

        # Fetch season page
        season_compact = make_season_compact(season_str)
        fetch_result = self.client.fetch_season_page(season_compact)
        if not fetch_result.ok:
            return YucParseResult(
                ok=False,
                operation=operation,
                error_type=fetch_result.error_type,
                error_message=fetch_result.error_message,
            )

        # Parse season page
        url = build_season_url(self.config.base_url, season_str)
        parse_result, parse_diags = parse_season_page(
            fetch_result.content, season_str, url, self.config
        )
        diagnostics.extend(parse_diags)

        # Check for critical parse failure
        if not parse_result.weekly_records:
            return YucParseResult(
                ok=False,
                operation=operation,
                error_type=ErrorType.PARSE_ZERO_ITEMS,
                error_message="Page returned 200 but no schedule items were parsed",
                diagnostics=diagnostics,
            )

        # Build result data
        result_data = _build_weekly_schedule_data(parse_result, weekday)
        if weekday is not None and not result_data["days"]:
            diagnostics.append(not_found_diag(f"No anime on weekday {weekday}"))

        return YucParseResult(
            ok=True,
            operation=operation,
            data=result_data,
            diagnostics=diagnostics,
        )

    def search_anime(
        self,
        query: str,
        season: str = "current",
        limit: int = 5,
    ) -> YucParseResult:
        """Search anime by query within a season."""
        operation = "yuc_search_anime"
        diagnostics = []

        # Validate query
        query = query.strip()
        if not query:
            return YucParseResult(
                ok=False,
                operation=operation,
                error_type=ErrorType.INVALID_PARAMS,
                error_message="query cannot be empty",
            )

        # Validate limit
        if not isinstance(limit, int) or limit < 1 or limit > 50:
            return YucParseResult(
                ok=False,
                operation=operation,
                error_type=ErrorType.INVALID_PARAMS,
                error_message="limit must be between 1 and 50",
            )

        # Get full weekly schedule
        schedule_result = self.get_weekly_schedule(season=season, weekday=None)
        if not schedule_result.ok:
            return schedule_result

        # Flatten items from all days
        all_items = []
        for day in schedule_result.data.get("days", []):
            all_items.extend(day.get("items", []))

        if not all_items:
            return YucParseResult(
                ok=True,
                operation=operation,
                data=[],
                diagnostics=[not_found_diag(f"No anime found for query: {query}")],
            )

        # Search through items
        matched = _search_items(all_items, query, limit)

        if not matched:
            return YucParseResult(
                ok=True,
                operation=operation,
                data=[],
                diagnostics=[not_found_diag(f"No match found for query: {query}")],
            )

        return YucParseResult(
            ok=True,
            operation=operation,
            data=matched,
            diagnostics=diagnostics,
        )

    def get_anime_detail(
        self,
        query: str,
        season: str = "current",
    ) -> YucParseResult:
        """Get anime detail by query."""
        operation = "yuc_get_anime_detail"

        # Search for anime
        search_result = self.search_anime(query, season, limit=5)
        if not search_result.ok:
            return search_result

        items = search_result.data or []

        if not items:
            return YucParseResult(
                ok=True,
                operation=operation,
                data=None,
                error_type=ErrorType.NOT_FOUND,
                error_message=f"No anime found matching: {query}",
            )

        # Check for unique match
        if len(items) == 1:
            return YucParseResult(
                ok=True,
                operation=operation,
                data=items[0],
            )

        # Multiple candidates - return list with ambiguous match
        # Sort by confidence descending
        items.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        top_confidence = items[0].get("confidence", 0)

        # If top confidence is very high (>=0.95), consider it unique
        if top_confidence >= 0.95:
            return YucParseResult(
                ok=True,
                operation=operation,
                data=items[0],
            )

        # Multiple similar matches
        return YucParseResult(
            ok=False,
            operation=operation,
            data=items,
            error_type=ErrorType.AMBIGUOUS_MATCH,
            error_message=f"Multiple matches found for '{query}', showing candidates",
            diagnostics=[ambiguous_match_diag(f"{len(items)} candidates returned")],
        )


def _build_weekly_schedule_data(parse_result: YucSeasonPageParse, weekday: Optional[int] = None) -> dict:
    """Build weekly schedule data structure from parsed records."""
    # Group records by weekday
    days_map = {i: [] for i in range(1, 8)}

    for record in parse_result.weekly_records:
        if record.weekday and 1 <= record.weekday <= 7:
            days_map[record.weekday].append(_record_to_item(record))

    # Filter by weekday if specified
    if weekday is not None and 1 <= weekday <= 7:
        filtered_days = [{"weekday": weekday, "label": _weekday_label(weekday), "items": days_map.get(weekday, [])}]
    else:
        filtered_days = [
            {"weekday": w, "label": _weekday_label(w), "items": days_map[w]}
            for w in range(1, 8)
            if days_map[w]
        ]

    return {
        "source": "yuc",
        "season": parse_result.season,
        "days": filtered_days,
    }


def _record_to_item(record) -> dict:
    """Convert YucWeeklySourceRecord to dict item."""
    item = {
        "source": "yuc",
        "external_id": None,
        "external_url": record.source_url,
        "season": record.season,
        "title_cn": record.title_cn,
        "title_jp": None,
        "title_en": None,
        "aliases": [],
        "weekday": record.weekday,
        "air_time": record.air_time,
        "start_date": record.start_date,
        "timezone": "Asia/Shanghai",
        "description": record.note,
        "cover_url": record.cover_url,
        "official_url": None,
        "platform_links": [link.model_dump() if hasattr(link, "model_dump") else link for link in record.platform_links],
        "confidence": 1.0,
    }
    return item


def _weekday_label(weekday: int) -> str:
    """Get Chinese label for weekday."""
    labels = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}
    return labels.get(weekday, f"星期{weekday}")


def _search_items(items: List[dict], query: str, limit: int) -> List[dict]:
    """Search items by query with simple matching."""
    query_lower = query.lower().strip()
    matched = []
    matched_ids = set()  # Track matched items to avoid duplicates

    for item in items:
        # Use id as proxy for item identity
        item_id = id(item)
        if item_id in matched_ids:
            continue

        title_cn = item.get("title_cn", "") or ""
        aliases = item.get("aliases", []) or []

        # Exact match on title_cn - highest priority
        if title_cn.lower() == query_lower:
            item["confidence"] = 1.0
            matched.append(item)
            matched_ids.add(item_id)
            continue

        # Exact match on aliases
        for alias in aliases:
            if alias.lower() == query_lower:
                item["confidence"] = 0.95
                matched.append(item)
                matched_ids.add(item_id)
                break  # Found exact alias match, no need to check contains

        if item_id in matched_ids:
            continue

        # Contains match on title_cn
        if query_lower in title_cn.lower():
            item["confidence"] = 1.0 if title_cn.lower() == f"精确{query_lower}" else 0.85
            matched.append(item)
            matched_ids.add(item_id)
            continue

        # Contains match on aliases
        for alias in aliases:
            if query_lower in alias.lower():
                item["confidence"] = 0.8
                matched.append(item)
                matched_ids.add(item_id)
                break

    # Sort by confidence descending, then title length ascending. Use a stable
    # title tie-breaker so equal contains matches do not depend on input order.
    matched.sort(key=cmp_to_key(_compare_search_result))

    return matched[:limit]


def _compare_search_result(left: dict, right: dict) -> int:
    """Compare two search results."""
    left_confidence = left.get("confidence", 0)
    right_confidence = right.get("confidence", 0)
    if left_confidence != right_confidence:
        return -1 if left_confidence > right_confidence else 1

    left_title = left.get("title_cn", "") or ""
    right_title = right.get("title_cn", "") or ""
    if len(left_title) != len(right_title):
        return -1 if len(left_title) < len(right_title) else 1

    if left_title == right_title:
        return 0
    return -1 if left_title > right_title else 1


# Module-level convenience functions
_default_service: Optional[YucService] = None


def get_default_service() -> YucService:
    """Get or create default service instance."""
    global _default_service
    if _default_service is None:
        _default_service = YucService()
    return _default_service


def get_current_season() -> YucParseResult:
    """Get current season using default service."""
    return get_default_service().get_current_season()


def get_weekly_schedule(season: str = "current", weekday: Optional[int] = None) -> YucParseResult:
    """Get weekly schedule using default service."""
    return get_default_service().get_weekly_schedule(season, weekday)


def search_anime(query: str, season: str = "current", limit: int = 5) -> YucParseResult:
    """Search anime using default service."""
    return get_default_service().search_anime(query, season, limit)


def get_anime_detail(query: str, season: str = "current") -> YucParseResult:
    """Get anime detail using default service."""
    return get_default_service().get_anime_detail(query, season)
