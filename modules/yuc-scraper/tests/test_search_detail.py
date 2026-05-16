"""Tests for yuc-scraper search and detail operations."""

import pytest

from yuc_scraper.service import _search_items, _weekday_label


class TestSearchItems:
    def test_exact_title_match(self):
        """Test exact title match returns confidence 1.0."""
        items = [
            {"title_cn": "测试动漫", "aliases": [], "confidence": 1.0},
        ]
        matched = _search_items(items, "测试动漫", limit=5)
        assert len(matched) == 1
        assert matched[0]["confidence"] == 1.0

    def test_alias_exact_match(self):
        """Test exact alias match returns confidence 0.95."""
        items = [
            {"title_cn": "测试动漫", "aliases": ["别名A"], "confidence": 1.0},
        ]
        matched = _search_items(items, "别名A", limit=5)
        assert len(matched) == 1
        assert matched[0]["confidence"] == 0.95

    def test_contains_match(self):
        """Test contains match returns confidence 0.85."""
        items = [
            {"title_cn": "这是一个很长的测试动漫名称", "aliases": [], "confidence": 1.0},
        ]
        matched = _search_items(items, "测试", limit=5)
        assert len(matched) == 1
        assert matched[0]["confidence"] == 0.85

    def test_alias_contains_match(self):
        """Test alias contains match returns confidence 0.8."""
        items = [
            {"title_cn": "测试动漫", "aliases": ["很长的别名"], "confidence": 1.0},
        ]
        matched = _search_items(items, "很长", limit=5)
        assert len(matched) == 1
        assert matched[0]["confidence"] == 0.8

    def test_no_match(self):
        """Test no match returns empty list."""
        items = [
            {"title_cn": "测试动漫", "aliases": [], "confidence": 1.0},
        ]
        matched = _search_items(items, "不存在", limit=5)
        assert len(matched) == 0

    def test_limit_applied(self):
        """Test that limit is applied."""
        items = [
            {"title_cn": f"动漫{i}", "aliases": [], "confidence": 1.0}
            for i in range(10)
        ]
        matched = _search_items(items, "动漫", limit=3)
        assert len(matched) == 3

    def test_sort_by_confidence_desc(self):
        """Test results are sorted by confidence descending."""
        items = [
            {"title_cn": "包含匹配", "aliases": [], "confidence": 1.0},
            {"title_cn": "精确匹配", "aliases": [], "confidence": 1.0},
        ]
        matched = _search_items(items, "匹配", limit=5)
        assert matched[0]["title_cn"] == "精确匹配"
        assert matched[0]["confidence"] == 1.0


class TestWeekdayLabel:
    def test_weekday_labels(self):
        """Test weekday label mapping."""
        assert _weekday_label(1) == "周一"
        assert _weekday_label(2) == "周二"
        assert _weekday_label(3) == "周三"
        assert _weekday_label(4) == "周四"
        assert _weekday_label(5) == "周五"
        assert _weekday_label(6) == "周六"
        assert _weekday_label(7) == "周日"