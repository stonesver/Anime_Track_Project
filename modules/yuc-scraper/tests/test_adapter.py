"""Tests for yuc to anime-parser adapter."""

from yuc_scraper.adapter import yuc_weekly_record_to_source_record
from yuc_scraper.models import YucDetailSourceRecord, YucPlatformLink, YucWeeklySourceRecord


def test_yuc_weekly_record_to_source_record_maps_parser_fields():
    record = YucWeeklySourceRecord(
        season="2026-04",
        weekday=3,
        weekday_label="周三",
        air_time="24:30",
        start_date="4/1~",
        note="首播",
        title_text="动漫名称\nAnime Name",
        title_cn="动漫名称 Anime Name",
        cover_url="//img.example.test/cover.jpg",
        platform_links=[
            YucPlatformLink(
                url="/watch/1",
                label="示例平台",
                region="大陆",
                kind="streaming",
            )
        ],
        source_url="https://yuc.wiki/202604/",
        selector_hits={"title": 1},
    )
    detail = YucDetailSourceRecord(
        season="2026-04",
        title_text="动漫名称 / Anime Name",
        title_cn="动漫名称",
        types=["TV", "原创"],
        tags=["原创", "科幻"],
        staff=["导演: 监督A"],
        cast=["配音: 声优A, 声优B"],
        official_url="/official",
        broadcast_text="每周三播出",
        source_url="https://yuc.wiki/202604/",
        selector_hits={"official_url": 1},
    )

    source_record = yuc_weekly_record_to_source_record(record, detail)

    assert source_record.source == "yuc"
    assert source_record.season_raw == "2026-04"
    assert source_record.title_raw == "动漫名称\nAnime Name"
    assert source_record.title_cn_raw == "动漫名称"
    assert "Anime Name" in source_record.aliases_raw
    assert source_record.weekday_raw == "周三"
    assert source_record.air_time_raw == "24:30"
    assert source_record.start_date_raw == "4/1~"
    assert source_record.types_raw == ["TV", "原创"]
    assert source_record.tags_raw == ["原创", "科幻"]
    assert source_record.staff_raw == ["导演: 监督A"]
    assert source_record.cast_raw == ["配音: 声优A, 声优B"]
    assert source_record.cover_url_raw == "https://img.example.test/cover.jpg"
    assert source_record.official_url_raw == "https://yuc.wiki/official"
    assert source_record.platform_links_raw[0].url == "https://yuc.wiki/watch/1"
    assert source_record.description_raw == "首播；每周三播出"
