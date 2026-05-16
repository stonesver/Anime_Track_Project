"""Configuration for yuc.wiki scraping."""

import re
from dataclasses import dataclass, field


def _default_href_pattern(href: str) -> bool:
    return bool(re.match(r"^/[0-9]{6}/?$", href))


def _default_text_pattern(text: str) -> bool:
    return bool(re.search(r'[0-9]{4}年[014][0-9]月新番', text))


@dataclass
class SeasonListRule:
    """Rule for parsing season links from home page."""
    link_selector: str = "a[href]"
    href_pattern: callable = field(default_factory=lambda: _default_href_pattern)
    text_pattern: callable = field(default_factory=lambda: _default_text_pattern)


@dataclass
class WeeklyRule:
    """Rule for parsing weekly schedule from season page."""
    article_selector: str = ".post-body"
    weekday_selector: str = "td.date2"
    item_container_strategy: str = "siblings_until_next_weekday_marker"
    time_selector: str = ".div_date .imgtext4, .div_date .imgtext5"
    start_or_note_selector: str = ".div_date .imgep2, .div_date .imgep"
    cover_selector: str = ".div_date img"
    cover_attr_priority: tuple = ("data-src", "src")
    title_selector: str = "td.date_title_, td.date_title__"
    platform_link_selector: str = "tr.tr_area a"
    platform_area_selector: str = ".area, .area_c"


@dataclass
class DetailRule:
    """Rule for parsing anime detail from season page."""
    article_selector: str = ".post-body"
    detail_title_selector: str = "td.title_main_r"
    title_cn_selector: str = ".title_cn_r, .title_cn_r2, .title_cn_r3"
    type_selector: str = ".type_c_r, .type_d_r, .type_e_r"
    tag_selector: str = ".type_tag_r"
    staff_selector: str = ".staff_r, .staff_r1"
    cast_selector: str = ".cast_r"
    official_link_selector: str = ".link_a_r a"
    broadcast_selector: str = ".broadcast_r, .broadcast_ex_r"


@dataclass
class YucScrapeConfig:
    """Main configuration for yuc scraper."""
    source: str = "yuc"
    base_url: str = "https://yuc.wiki"
    home_path: str = "/"
    season_path_template: str = "/{season_compact}/"
    list_seasons: SeasonListRule = field(default_factory=SeasonListRule)
    weekly: WeeklyRule = field(default_factory=WeeklyRule)
    detail: DetailRule = field(default_factory=DetailRule)


# Default configuration instance
DEFAULT_CONFIG = YucScrapeConfig()


def make_season_compact(season: str) -> str:
    """Convert YYYY-MM or YYYYMM to yuc path format YYYYMM."""
    cleaned = season.replace("-", "").replace("年", "")
    if len(cleaned) == 6 and cleaned.isdigit():
        month = cleaned[4:6]
        if month not in ("01", "04", "07", "10"):
            raise ValueError(f"Invalid anime season month: {season}")
        return cleaned
    raise ValueError(f"Invalid season format: {season}")


def parse_season_from_compact(compact: str) -> str:
    """Convert YYYYMM to YYYY-MM format."""
    if len(compact) == 6 and compact.isdigit():
        year = compact[:4]
        month = compact[4:6]
        return f"{year}-{month}"
    raise ValueError(f"Invalid compact season: {compact}")