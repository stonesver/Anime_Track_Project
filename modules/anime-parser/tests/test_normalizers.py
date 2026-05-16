"""Tests for normalizers module."""

import pytest

from anime_parser.normalizers import (
    clean_display_text,
    normalize_air_time,
    normalize_season,
    normalize_start_date,
    normalize_title_for_match,
    normalize_url,
    normalize_weekday,
)


class TestNormalizeSeason:
    def test_yyyymm_format(self):
        assert normalize_season("202604").value == "2026-04"

    def test_yyyy_mm_format(self):
        assert normalize_season("2026-04").value == "2026-04"

    def test_yyyy_year_month_format(self):
        assert normalize_season("2026年4月").value == "2026-04"

    def test_yyyy_year_month_padded(self):
        assert normalize_season("2026年04月").value == "2026-04"

    def test_invalid_month(self):
        result = normalize_season("202603")
        assert result.value is None
        assert result.diagnostic is not None

    def test_invalid_format(self):
        result = normalize_season("invalid")
        assert result.value is None

    def test_none_input(self):
        result = normalize_season(None)
        assert result.value is None


class TestNormalizeWeekday:
    def test_chinese_weekday(self):
        assert normalize_weekday("周三").value == 3
        assert normalize_weekday("周一").value == 1

    def test_chinese_weekday_full(self):
        assert normalize_weekday("星期三").value == 3
        assert normalize_weekday("星期一").value == 1

    def test_japanese_weekday(self):
        assert normalize_weekday("水").value == 3
        assert normalize_weekday("月").value == 1

    def test_english_weekday(self):
        assert normalize_weekday("wed").value == 3
        assert normalize_weekday("MON").value == 1

    def test_integer_weekday(self):
        assert normalize_weekday(3).value == 3
        assert normalize_weekday(1).value == 1

    def test_invalid_integer(self):
        result = normalize_weekday(8)
        assert result.value is None

    def test_no_fixed_weekday(self):
        assert normalize_weekday("网络放送").value is None
        assert normalize_weekday("未定").value is None
        assert normalize_weekday("待定").value is None

    def test_invalid_weekday(self):
        result = normalize_weekday("abc")
        assert result.value is None
        assert result.diagnostic is not None

    def test_none_input(self):
        assert normalize_weekday(None).value is None


class TestNormalizeAirTime:
    def test_standard_time(self):
        assert normalize_air_time("22:00~").value == "22:00"
        assert normalize_air_time("7:05").value == "07:05"

    def test_late_night_time(self):
        assert normalize_air_time("24:30~").value == "24:30"
        assert normalize_air_time("25:00").value == "25:00"

    def test_no_time(self):
        assert normalize_air_time("年番").value is None
        assert normalize_air_time("待定").value is None

    def test_none_input(self):
        assert normalize_air_time(None).value is None


class TestNormalizeStartDate:
    def test_yyyy_mm_dd_format(self):
        assert normalize_start_date("2026-04-01", "2026-04").value == "2026-04-01"

    def test_mm_dd_format(self):
        assert normalize_start_date("4/1", "2026-04").value == "2026-04-01"

    def test_mm_dd_with_trailing(self):
        assert normalize_start_date("4/1~", "2026-04").value == "2026-04-01"

    def test_no_year_in_input(self):
        result = normalize_start_date("4/1", None)
        assert result.value is None

    def test_none_input(self):
        assert normalize_start_date(None, "2026-04").value is None


class TestCleanDisplayText:
    def test_br_to_space(self):
        assert clean_display_text("title<br>subtitle") == "title subtitle"

    def test_multiple_spaces(self):
        assert clean_display_text("title    subtitle") == "title subtitle"

    def test_strip_whitespace(self):
        assert clean_display_text("  title  ") == "title"

    def test_none_input(self):
        assert clean_display_text(None) is None


class TestNormalizeTitleForMatch:
    def test_nfkc_normalization(self):
        assert normalize_title_for_match("１") == normalize_title_for_match("1")

    def test_lowercase(self):
        assert normalize_title_for_match("ABC") == "abc"

    def test_remove_spaces(self):
        assert normalize_title_for_match("abc def") == "abcdef"

    def test_remove_punctuation(self):
        result = normalize_title_for_match("1. 2. 3")
        assert "1" in result

    def test_none_input(self):
        assert normalize_title_for_match(None) == ""


class TestNormalizeUrl:
    def test_absolute_http_url(self):
        assert normalize_url("https://example.com/page").value == "https://example.com/page"
        assert normalize_url("http://example.com/page").value == "http://example.com/page"

    def test_relative_url_with_base(self):
        result = normalize_url("/page", "https://example.com/base")
        assert result.value == "https://example.com/page"

    def test_invalid_protocol(self):
        result = normalize_url("ftp://example.com")
        assert result.value is None

    def test_none_input(self):
        assert normalize_url(None).value is None