"""Parser for yuc.wiki HTML pages."""

import re
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup, Tag

from yuc_scraper.config import DEFAULT_CONFIG, parse_season_from_compact, YucScrapeConfig
from yuc_scraper.errors import (
    ErrorType,
    parse_schema_changed_diag,
    parse_zero_items_diag,
)
from yuc_scraper.html import get_text, get_text_with_br
from yuc_scraper.models import (
    Diagnostic,
    YucDetailSourceRecord,
    YucPlatformLink,
    YucSeasonLink,
    YucSeasonPageParse,
    YucWeeklySourceRecord,
)


WEEKDAY_MAP = {
    "周一": 1, "周二": 2, "周三": 3, "周四": 4, "周五": 5, "周六": 6, "周日": 7,
    "星期一": 1, "星期二": 2, "星期三": 3, "星期四": 4, "星期五": 5, "星期六": 6, "星期日": 7,
    "月": 1, "火": 2, "水": 3, "木": 4, "金": 5, "土": 6, "日": 7,
    "Mon": 1, "Tue": 2, "Wed": 3, "Thu": 4, "Fri": 5, "Sat": 6, "Sun": 7,
}


def parse_season_links(html: str, config: YucScrapeConfig = DEFAULT_CONFIG) -> Tuple[List[YucSeasonLink], List[Diagnostic]]:
    """Parse season links from home page HTML.

    Returns:
        Tuple of (season_links, diagnostics)
    """
    diagnostics = []
    if not html or len(html.strip()) == 0:
        return [], [Diagnostic(code=ErrorType.SOURCE_UNAVAILABLE, message="Empty HTML", severity="error")]

    soup = BeautifulSoup(html, "html.parser")
    links = soup.select(config.list_seasons.link_selector)

    season_links: List[YucSeasonLink] = []
    seen_seasons: set = set()

    for link in links:
        href = link.get("href", "")
        text = link.get_text(strip=True)

        # Check href pattern
        if not config.list_seasons.href_pattern(href):
            continue

        # Check text pattern. yuc sometimes prefixes the latest season with New,
        # so the match must not require the year to be the first token.
        if not config.list_seasons.text_pattern(text):
            continue

        # Extract compact season from href
        match = re.search(r"/([0-9]{6})/?", href)
        if not match:
            continue

        compact = match.group(1)
        year = compact[:4]
        month = compact[4:6]

        # Validate month
        if month not in ("01", "04", "07", "10"):
            diagnostics.append(Diagnostic(
                code="invalid_month",
                message=f"Invalid month in season: {text}",
                raw_value=month,
                severity="info",
            ))
            continue

        try:
            season = parse_season_from_compact(compact)
        except ValueError:
            continue

        # Check for New marker
        is_new = bool(re.search(r"(\(?New\)?|（New）)", text, re.IGNORECASE))

        # Build absolute URL
        base_url = config.base_url.rstrip("/")
        url = f"{base_url}{href.rstrip('/')}/"

        if season in seen_seasons:
            continue
        seen_seasons.add(season)

        season_links.append(YucSeasonLink(
            season=season,
            season_compact=compact,
            url=url,
            text=text,
            is_new=is_new,
        ))

    season_links.sort(key=lambda link: link.season, reverse=True)

    if not season_links:
        diagnostics.append(Diagnostic(
            code=ErrorType.PARSE_SCHEMA_CHANGED,
            message="No valid season links found",
            severity="error",
        ))

    return season_links, diagnostics


def select_current_season(links: List[YucSeasonLink]) -> Tuple[Optional[YucSeasonLink], List[Diagnostic]]:
    """Select current season from parsed links.

    Priority:
    1. is_new = true with valid season
    2. Latest valid season by year-month
    """
    diagnostics = []

    if not links:
        return None, [Diagnostic(code=ErrorType.PARSE_ZERO_ITEMS, message="No season links to select from", severity="error")]

    # Filter valid seasons
    valid_links = [l for l in links if l.season is not None]

    # Priority 1: New marked
    new_links = [l for l in valid_links if l.is_new]
    if new_links:
        # Sort by season descending
        new_links.sort(key=lambda x: x.season, reverse=True)
        return new_links[0], diagnostics

    # Priority 2: Latest by year-month
    valid_links.sort(key=lambda x: x.season, reverse=True)
    return valid_links[0] if valid_links else None, diagnostics


def parse_weekday(text: str) -> Optional[int]:
    """Parse weekday text to integer 1-7."""
    text = text.strip()

    # Direct number
    if text.isdigit() and 1 <= int(text) <= 7:
        return int(text)

    # Chinese weekday
    for key, value in WEEKDAY_MAP.items():
        if key in text:
            return value

    return None


def parse_season_page(
    html: str,
    season: str,
    source_url: str,
    config: YucScrapeConfig = DEFAULT_CONFIG,
) -> Tuple[YucSeasonPageParse, List[Diagnostic]]:
    """Parse season page HTML into weekly and detail records.

    Returns:
        Tuple of (parse_result, diagnostics)
    """
    diagnostics = []

    if not html or len(html.strip()) == 0:
        result = YucSeasonPageParse(
            season=season,
            source_url=source_url,
            diagnostics=[Diagnostic(code=ErrorType.SOURCE_UNAVAILABLE, message="Empty HTML", severity="error")],
        )
        return result, diagnostics

    soup = BeautifulSoup(html, "html.parser")

    # Find article area
    article = soup.select_one(config.weekly.article_selector)
    if not article:
        return YucSeasonPageParse(
            season=season,
            source_url=source_url,
            diagnostics=[Diagnostic(code=ErrorType.PARSE_SCHEMA_CHANGED, message="Article selector not found", severity="error")],
        ), diagnostics

    # Parse weekly records
    weekly_records = parse_weekly_records(article, season, source_url, config)

    # Parse detail records
    detail_records = parse_detail_records(article, season, source_url, config)

    if not weekly_records and not detail_records:
        diagnostics.append(Diagnostic(
            code=ErrorType.PARSE_ZERO_ITEMS,
            message="No weekly or detail records parsed",
            severity="error",
        ))

    result = YucSeasonPageParse(
        season=season,
        source_url=source_url,
        weekly_records=weekly_records,
        detail_records=detail_records,
        diagnostics=diagnostics,
    )

    return result, diagnostics


def parse_weekly_records(
    article,
    season: str,
    source_url: str,
    config: YucScrapeConfig = DEFAULT_CONFIG,
) -> List[YucWeeklySourceRecord]:
    """Parse weekly schedule records from article element."""
    records = []

    # yuc's generated HTML does not keep weekday markers and anime rows in one
    # table sibling chain. Scan the article in document order and assign each
    # title cell to the latest weekday marker seen before it.
    weekday_markers = article.select(config.weekly.weekday_selector)
    title_cells = article.select(config.weekly.title_selector)
    weekday_marker_ids = {id(marker) for marker in weekday_markers}
    title_cell_ids = {id(title_cell) for title_cell in title_cells}
    current_weekday: Optional[int] = None
    current_weekday_label: Optional[str] = None

    for node in article.descendants:
        if not isinstance(node, Tag):
            continue

        if id(node) in weekday_marker_ids:
            current_weekday_label = node.get_text(strip=True)
            current_weekday = parse_weekday(current_weekday_label)
            continue

        if id(node) in title_cell_ids:
            item_container = _find_weekly_item_container(node, config)
            record = _parse_weekly_item(
                item_container, season, source_url,
                current_weekday, current_weekday_label, config,
            )
            if record:
                records.append(record)

    return records


def _find_weekly_item_container(title_cell: Tag, config: YucScrapeConfig) -> Tag:
    """Find the smallest ancestor that contains one weekly anime item."""
    current: Optional[Tag] = title_cell
    while current is not None:
        if (
            current.select_one(config.weekly.title_selector)
            and (
                current.select_one(config.weekly.time_selector)
                or current.select_one(config.weekly.start_or_note_selector)
                or current.select_one(config.weekly.cover_selector)
            )
        ):
            return current
        current = current.parent if isinstance(current.parent, Tag) else None

    return title_cell.find_parent("tr") or title_cell


def _parse_weekly_item(row, season, source_url, weekday, weekday_label, config):
    """Parse a single weekly schedule row into YucWeeklySourceRecord."""
    selector_hits = {}

    # Title
    title_cell = row.select_one(config.weekly.title_selector)
    title_text = None
    title_cn = None
    if title_cell:
        title_text = get_text_with_br(title_cell)
        selector_hits["title"] = 1

        # Keep all title lines; yuc often splits one Chinese title with <br>.
        if title_text:
            title_cn = re.sub(r"\s+", " ", title_text).strip()

    # Time
    time_cell = row.select_one(config.weekly.time_selector)
    air_time = None
    if time_cell:
        time_text = time_cell.get_text(strip=True)
        if time_text and time_text not in ("待定", "年番"):
            air_time = time_text
        selector_hits["time"] = 1

    # Start date / note
    date_cell = row.select_one(config.weekly.start_or_note_selector)
    start_date = None
    note = None
    if date_cell:
        date_text = date_cell.get_text(strip=True)
        if date_text:
            if "~" in date_text and "/" in date_text:
                # Likely a date range like 4/1~
                start_date = date_text
                note = None
            elif date_text in ("年番", "待定"):
                start_date = None
                note = date_text
            else:
                # Unknown, put in note
                note = date_text
        selector_hits["date"] = 1

    # Cover
    cover_url = None
    cover_img = row.select_one(config.weekly.cover_selector)
    if cover_img:
        for attr in config.weekly.cover_attr_priority:
            if cover_img.has_attr(attr):
                cover_url = cover_img.get(attr)
                selector_hits["cover"] = 1
                break

    # Platform links
    platform_links = []
    for link in row.select(config.weekly.platform_link_selector):
        href = link.get("href", "")
        label = link.get_text(strip=True)

        # Find region nearby
        region = None
        area_el = None
        platform_row = link.find_parent("tr")
        if platform_row:
            area_el = platform_row.select_one(config.weekly.platform_area_selector)
        if area_el:
            region = area_el.get_text(strip=True)

        platform_links.append(YucPlatformLink(
            url=href if href.startswith("http") else None,
            label=label,
            region=region,
            kind="streaming",
        ))
    if platform_links:
        selector_hits["platform"] = len(platform_links)

    if not title_text:
        return None

    return YucWeeklySourceRecord(
        season=season,
        weekday=weekday,
        weekday_label=weekday_label,
        air_time=air_time,
        start_date=start_date,
        note=note,
        title_text=title_text,
        title_cn=title_cn,
        cover_url=cover_url,
        platform_links=platform_links,
        source_url=source_url,
        selector_hits=selector_hits,
    )


def parse_detail_records(
    article,
    season: str,
    source_url: str,
    config: YucScrapeConfig = DEFAULT_CONFIG,
) -> List[YucDetailSourceRecord]:
    """Parse anime detail records from article element."""
    records = []

    detail_titles = article.select(config.detail.detail_title_selector)

    for title_el in detail_titles:
        selector_hits = {}

        container = _find_detail_container(title_el, config)
        if not container:
            continue

        # Title text with line breaks preserved
        title_text = get_text_with_br(title_el)
        selector_hits["detail_title"] = 1

        # Chinese title
        title_cn = None
        cn_el = container.select_one(config.detail.title_cn_selector)
        if cn_el:
            title_cn = cn_el.get_text(strip=True)
            selector_hits["title_cn"] = 1

        # Japanese title
        title_jp = None
        # yuc may not have explicit jp title selector, use sibling or next element
        title_jp = None

        # Types
        types = []
        for type_el in container.select(config.detail.type_selector):
            types.append(type_el.get_text(strip=True))
        if types:
            selector_hits["types"] = len(types)

        # Tags
        tags = []
        for tag_el in container.select(config.detail.tag_selector):
            tags.append(tag_el.get_text(strip=True))
        if tags:
            selector_hits["tags"] = len(tags)

        # Staff
        staff = []
        for staff_el in container.select(config.detail.staff_selector):
            staff.append(staff_el.get_text(strip=True))
        if staff:
            selector_hits["staff"] = len(staff)

        # Cast
        cast = []
        for cast_el in container.select(config.detail.cast_selector):
            cast.append(cast_el.get_text(strip=True))
        if cast:
            selector_hits["cast"] = len(cast)

        # Official URL
        official_url = None
        official_link = container.select_one(config.detail.official_link_selector)
        if official_link:
            official_url = official_link.get("href")
            selector_hits["official_url"] = 1

        # Broadcast text
        broadcast_text = None
        broadcast_el = container.select_one(config.detail.broadcast_selector)
        if broadcast_el:
            broadcast_text = broadcast_el.get_text(strip=True)
            selector_hits["broadcast"] = 1

        record = YucDetailSourceRecord(
            season=season,
            title_text=title_text,
            title_cn=title_cn,
            title_jp=title_jp,
            types=types,
            tags=tags,
            staff=staff,
            cast=cast,
            official_url=official_url,
            broadcast_text=broadcast_text,
            source_url=source_url,
            selector_hits=selector_hits,
        )
        records.append(record)

    return records


def _find_detail_container(title_el: Tag, config: YucScrapeConfig) -> Optional[Tag]:
    """Find the smallest detail block that belongs to one anime."""
    table = title_el.find_parent("table")
    if table and len(table.select(config.detail.detail_title_selector)) == 1:
        return table

    row = title_el.find_parent("tr")
    if row:
        return row

    return title_el.find_parent()
