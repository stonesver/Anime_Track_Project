"""Tests for service module."""

import pytest

from anime_parser.models import (
    AnimeItem,
    ScheduleDay,
    SourceAnimeRecord,
    WeeklySchedule,
)
from anime_parser.service import normalize_anime, normalize_weekly_schedule


class TestNormalizeAnime:
    def test_complete_record(self):
        record = SourceAnimeRecord(
            source="yuc",
            source_url="https://yuc.wiki/202604/",
            source_id="123",
            season_raw="202604",
            title_raw="测试番剧",
            title_cn_raw="测试番剧",
            weekday_raw="周三",
            air_time_raw="24:30~",
            start_date_raw="4/1~",
            description_raw="简介",
            cover_url_raw="https://example.com/cover.jpg",
        )
        result = normalize_anime(record)
        assert result.ok is True
        assert result.data is not None
        assert result.data.title_cn == "测试番剧"
        assert result.data.season == "2026-04"
        assert result.data.weekday == 3
        assert result.data.air_time == "24:30"
        assert result.data.start_date == "2026-04-01"

    def test_missing_title(self):
        record = SourceAnimeRecord(
            source="yuc",
            title_raw=None,
            title_cn_raw=None,
            title_jp_raw=None,
        )
        result = normalize_anime(record)
        assert result.ok is False
        assert result.error_type == "missing_title"

    def test_missing_source(self):
        record = SourceAnimeRecord(
            source="",
            title_raw="测试",
        )
        result = normalize_anime(record)
        assert result.ok is False
        assert result.error_type == "invalid_source_record"

    def test_optional_fields_missing(self):
        record = SourceAnimeRecord(
            source="yuc",
            title_raw="测试番剧",
        )
        result = normalize_anime(record)
        assert result.ok is True
        assert result.data is not None
        assert result.data.title_cn == "测试番剧"
        assert result.data.weekday is None
        assert result.data.air_time is None

    def test_chinese_weekday_normalization(self):
        record = SourceAnimeRecord(
            source="yuc",
            title_raw="测试",
            weekday_raw="周三",
        )
        result = normalize_anime(record)
        assert result.data.weekday == 3

    def test_invalid_season(self):
        record = SourceAnimeRecord(
            source="yuc",
            title_raw="测试",
            season_raw="invalid",
        )
        result = normalize_anime(record)
        assert result.ok is True  # Still succeeds but with diagnostic
        assert len(result.diagnostics) > 0


class TestNormalizeWeeklySchedule:
    def test_single_record(self):
        records = [
            SourceAnimeRecord(
                source="yuc",
                season_raw="202604",
                title_raw="测试番剧",
                weekday_raw="周三",
            )
        ]
        result = normalize_weekly_schedule("yuc", "2026-04", records)
        assert result.ok is True
        assert result.data is not None
        assert len(result.data.days) == 1
        assert result.data.days[0].weekday == 3

    def test_multiple_weekdays(self):
        records = [
            SourceAnimeRecord(
                source="yuc",
                season_raw="202604",
                title_raw="番剧1",
                weekday_raw="周一",
            ),
            SourceAnimeRecord(
                source="yuc",
                season_raw="202604",
                title_raw="番剧2",
                weekday_raw="周三",
            ),
            SourceAnimeRecord(
                source="yuc",
                season_raw="202604",
                title_raw="番剧3",
                weekday_raw="周三",
            ),
        ]
        result = normalize_weekly_schedule("yuc", "2026-04", records)
        assert result.ok is True
        assert len(result.data.days) == 2
        # Check that Wednesday has 2 items
        wed_day = next(d for d in result.data.days if d.weekday == 3)
        assert len(wed_day.items) == 2

    def test_empty_records(self):
        result = normalize_weekly_schedule("yuc", "2026-04", [])
        assert result.ok is False
        assert result.error_type == "parse_zero_items"

    def test_no_fixed_weekday(self):
        records = [
            SourceAnimeRecord(
                source="yuc",
                season_raw="202604",
                title_raw="网络放送番剧",
                weekday_raw="网络放送",
            )
        ]
        result = normalize_weekly_schedule("yuc", "2026-04", records)
        assert result.ok is True
        # Network broadcast items don't appear in days
        assert len(result.data.days) == 0

    def test_maintains_input_order(self):
        records = [
            SourceAnimeRecord(
                source="yuc",
                season_raw="202604",
                title_raw="番剧A",
                weekday_raw="周三",
            ),
            SourceAnimeRecord(
                source="yuc",
                season_raw="202604",
                title_raw="番剧B",
                weekday_raw="周三",
            ),
            SourceAnimeRecord(
                source="yuc",
                season_raw="202604",
                title_raw="番剧C",
                weekday_raw="周三",
            ),
        ]
        result = normalize_weekly_schedule("yuc", "2026-04", records)
        wed_day = next(d for d in result.data.days if d.weekday == 3)
        assert wed_day.items[0].title_cn == "番剧A"
        assert wed_day.items[1].title_cn == "番剧B"
        assert wed_day.items[2].title_cn == "番剧C"