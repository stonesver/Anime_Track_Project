"""Tests for yuc-scraper configuration."""

import pytest

from yuc_scraper.config import (
    DEFAULT_CONFIG,
    YucScrapeConfig,
    make_season_compact,
    parse_season_from_compact,
    SeasonListRule,
    WeeklyRule,
    DetailRule,
)


class TestYucScrapeConfig:
    def test_default_config_fields(self):
        assert DEFAULT_CONFIG.source == "yuc"
        assert DEFAULT_CONFIG.base_url == "https://yuc.wiki"
        assert DEFAULT_CONFIG.home_path == "/"
        assert DEFAULT_CONFIG.season_path_template == "/{season_compact}/"

    def test_season_list_rule_defaults(self):
        rule = DEFAULT_CONFIG.list_seasons
        assert rule.link_selector == "a[href]"
        assert rule.href_pattern is not None
        assert rule.text_pattern is not None

    def test_weekly_rule_defaults(self):
        rule = DEFAULT_CONFIG.weekly
        assert rule.article_selector == ".post-body"
        assert rule.weekday_selector == "td.date2"
        assert rule.title_selector == "td.date_title_, td.date_title__"
        assert len(rule.cover_attr_priority) == 2

    def test_detail_rule_defaults(self):
        rule = DEFAULT_CONFIG.detail
        assert rule.article_selector == ".post-body"
        assert rule.detail_title_selector == "td.title_main_r"
        assert rule.title_cn_selector == ".title_cn_r, .title_cn_r2, .title_cn_r3"


class TestMakeSeasonCompact:
    def test_valid_yyyy_mm(self):
        assert make_season_compact("2026-04") == "202604"
        assert make_season_compact("2026-01") == "202601"
        assert make_season_compact("2026-10") == "202610"

    def test_valid_yyyymm(self):
        assert make_season_compact("202604") == "202604"
        assert make_season_compact("202601") == "202601"

    def test_valid_months_only(self):
        """Test that only valid anime season months are accepted."""
        # Valid months: 01, 04, 07, 10
        assert make_season_compact("2026-04") == "202604"
        assert make_season_compact("2026-01") == "202601"
        assert make_season_compact("2026-07") == "202607"
        assert make_season_compact("2026-10") == "202610"
        # Invalid month should raise
        with pytest.raises(ValueError):
            make_season_compact("2026-13")
        with pytest.raises(ValueError):
            make_season_compact("2026-02")


class TestParseSeasonFromCompact:
    def test_valid_compact(self):
        assert parse_season_from_compact("202604") == "2026-04"
        assert parse_season_from_compact("202601") == "2026-01"
        assert parse_season_from_compact("202510") == "2025-10"

    def test_invalid_compact(self):
        with pytest.raises(ValueError):
            parse_season_from_compact("invalid")
        with pytest.raises(ValueError):
            parse_season_from_compact("20261")