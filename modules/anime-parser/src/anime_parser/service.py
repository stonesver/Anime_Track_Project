"""Service layer for anime parsing and scheduling."""

from typing import Any

from anime_parser.errors import (
    invalid_source_record_diag,
    missing_title_diag,
    parse_zero_items_diag,
)
from anime_parser.models import (
    AnimeItem,
    AnimeParseResult,
    PlatformLink,
    ScheduleDay,
    SourceAnimeRecord,
    WeeklySchedule,
)
from anime_parser.normalizers import (
    clean_display_text,
    normalize_air_time,
    normalize_platform_link,
    normalize_season,
    normalize_start_date,
    normalize_title_for_match,
    normalize_url,
    normalize_weekday,
)


WEEKDAY_LABELS = {
    1: "周一",
    2: "周二",
    3: "周三",
    4: "周四",
    5: "周五",
    6: "周六",
    7: "周日",
}


def normalize_anime(record: SourceAnimeRecord) -> AnimeParseResult[AnimeItem]:
    """Normalize a single source anime record to AnimeItem."""
    diagnostics = []
    operation = "normalize_anime"

    # Validate source
    if not record.source:
        return AnimeParseResult(
            ok=False,
            operation=operation,
            error_type="invalid_source_record",
            error_message="source is required",
            diagnostics=[invalid_source_record_diag("source is required")],
        )

    # Check title availability
    title_cn = record.title_cn_raw or record.title_raw
    title_jp = record.title_jp_raw
    title_en = record.title_en_raw
    title_raw = record.title_raw

    if not any([title_cn, title_jp, title_en, title_raw]):
        return AnimeParseResult(
            ok=False,
            source=record.source,
            operation=operation,
            error_type="missing_title",
            error_message="At least one title field is required",
            diagnostics=[missing_title_diag()],
        )

    # Normalize season
    season_result = normalize_season(record.season_raw)
    season = season_result.value
    if season_result.diagnostic:
        diagnostics.append(season_result.diagnostic)

    # Normalize weekday
    weekday_result = normalize_weekday(record.weekday_raw)
    weekday = weekday_result.value
    if weekday_result.diagnostic:
        diagnostics.append(weekday_result.diagnostic)

    # Normalize air time
    air_time_result = normalize_air_time(record.air_time_raw)
    air_time = air_time_result.value
    if air_time_result.diagnostic:
        diagnostics.append(air_time_result.diagnostic)

    # Normalize start date
    start_date_result = normalize_start_date(record.start_date_raw, season)
    start_date = start_date_result.value
    if start_date_result.diagnostic:
        diagnostics.append(start_date_result.diagnostic)

    # Clean display titles
    title_cn_clean = clean_display_text(title_cn)
    title_jp_clean = clean_display_text(title_jp)
    title_en_clean = clean_display_text(title_en)
    title_raw_clean = clean_display_text(title_raw)

    # Build aliases from raw aliases
    aliases = []
    for alias in record.aliases_raw:
        cleaned = clean_display_text(alias)
        if cleaned:
            aliases.append(cleaned)

    # Add title variants to aliases (non-primary titles)
    if title_cn_clean and title_raw_clean and title_cn_clean != title_raw_clean:
        pass  # title_raw already handled separately
    if title_jp_clean and title_cn_clean != title_jp_clean:
        pass  # handled separately as title_jp
    if title_en_clean and title_cn_clean != title_en_clean:
        pass  # handled separately as title_en

    # Normalize cover URL
    cover_url_result = normalize_url(record.cover_url_raw)
    cover_url = cover_url_result.value
    if cover_url_result.diagnostic:
        diagnostics.append(cover_url_result.diagnostic)

    # Normalize official URL
    official_url_result = normalize_url(record.official_url_raw)
    official_url = official_url_result.value
    if official_url_result.diagnostic:
        diagnostics.append(official_url_result.diagnostic)

    # Normalize platform links
    platform_links = []
    for raw_link in record.platform_links_raw:
        link_dict = raw_link.model_dump() if hasattr(raw_link, "model_dump") else raw_link
        platform_links.append(normalize_platform_link(link_dict))

    # Clean description
    description = clean_display_text(record.description_raw)

    # Build AnimeItem
    item = AnimeItem(
        source=record.source,
        external_id=record.source_id,
        external_url=record.source_url,
        season=season,
        title_cn=title_cn_clean,
        title_jp=title_jp_clean,
        title_en=title_en_clean,
        aliases=aliases,
        weekday=weekday,
        air_time=air_time,
        start_date=start_date,
        description=description,
        cover_url=cover_url,
        official_url=official_url,
        platform_links=platform_links,
        confidence=1.0,
    )

    return AnimeParseResult(
        ok=True,
        source=record.source,
        operation=operation,
        data=item,
        diagnostics=diagnostics,
    )


def normalize_weekly_schedule(
    source: str,
    season: str,
    records: list[SourceAnimeRecord],
) -> AnimeParseResult[WeeklySchedule]:
    """Normalize a list of source records to a weekly schedule."""
    diagnostics = []
    operation = "normalize_weekly_schedule"

    if not records:
        return AnimeParseResult(
            ok=False,
            source=source,
            operation=operation,
            error_type="parse_zero_items",
            error_message="No records provided",
            diagnostics=[parse_zero_items_diag()],
        )

    # Normalize season
    season_result = normalize_season(season)
    if not season_result.value:
        return AnimeParseResult(
            ok=False,
            source=source,
            operation=operation,
            error_type=season_result.diagnostic.code if season_result.diagnostic else "invalid_season",
            error_message=season_result.diagnostic.message if season_result.diagnostic else "Invalid season",
            diagnostics=[season_result.diagnostic] if season_result.diagnostic else [],
        )
    normalized_season = season_result.value

    # Normalize each record
    items_by_weekday: dict[int, list[AnimeItem]] = {1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: []}
    undated_items: list[AnimeItem] = []
    all_success = True

    for record in records:
        result = normalize_anime(record)
        if result.ok and result.data:
            item = result.data
            if item.weekday is not None and 1 <= item.weekday <= 7:
                items_by_weekday[item.weekday].append(item)
            else:
                undated_items.append(item)
        else:
            all_success = False

        if result.diagnostics:
            diagnostics.extend(result.diagnostics)

    # Build days
    days = []
    for weekday in range(1, 8):
        items = items_by_weekday[weekday]
        if items:
            days.append(ScheduleDay(
                weekday=weekday,
                label=WEEKDAY_LABELS[weekday],
                items=items,
            ))

    # Build weekly schedule
    schedule = WeeklySchedule(
        source=source,
        season=normalized_season,
        days=days,
    )

    # If all failed, return error
    if not days and undated_items:
        # No weekday items but have undated items
        pass

    if all_success:
        return AnimeParseResult(
            ok=True,
            source=source,
            operation=operation,
            data=schedule,
            diagnostics=diagnostics,
        )
    else:
        return AnimeParseResult(
            ok=True,
            source=source,
            operation=operation,
            data=schedule,
            diagnostics=diagnostics,
        )