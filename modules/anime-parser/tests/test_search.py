"""Tests for search module."""

import pytest

from anime_parser.models import AnimeItem
from anime_parser.search import search_anime_items


class TestSearchAnimeItems:
    def test_exact_title_match(self):
        items = [
            AnimeItem(source="yuc", title_cn="测试番剧"),
            AnimeItem(source="yuc", title_cn="其他番剧"),
        ]
        result = search_anime_items(items, "测试番剧")
        assert result.ok is True
        assert len(result.data) == 1
        assert result.data[0].title_cn == "测试番剧"
        assert result.data[0].confidence == 1.0

    def test_alias_match(self):
        items = [
            AnimeItem(source="yuc", title_cn="测试番剧", aliases=["别名番剧"]),
        ]
        result = search_anime_items(items, "别名番剧")
        assert result.ok is True
        assert len(result.data) == 1
        # Alias exact match returns with original confidence from normalization
        assert result.data[0].title_cn == "测试番剧"

    def test_title_contains_match(self):
        items = [
            AnimeItem(source="yuc", title_cn="测试长番剧名"),
        ]
        result = search_anime_items(items, "测试")
        assert result.ok is True
        assert len(result.data) == 1
        # Title contains match returns with original confidence from normalization
        assert result.data[0].title_cn == "测试长番剧名"

    def test_normalized_match(self):
        items = [
            AnimeItem(source="yuc", title_cn="测试番剧"),
        ]
        result = search_anime_items(items, "测试番剧")
        assert result.ok is True

    def test_no_match(self):
        items = [
            AnimeItem(source="yuc", title_cn="测试番剧"),
        ]
        result = search_anime_items(items, "不存在的番剧")
        assert result.ok is True
        assert len(result.data) == 0

    def test_limit(self):
        items = [
            AnimeItem(source="yuc", title_cn=f"番剧{i}") for i in range(10)
        ]
        result = search_anime_items(items, "番剧", limit=3)
        assert result.ok is True
        assert len(result.data) == 3

    def test_empty_query(self):
        items = [AnimeItem(source="yuc", title_cn="测试番剧")]
        result = search_anime_items(items, "")
        assert result.ok is False
        assert result.error_type == "invalid_params"

    def test_whitespace_query(self):
        items = [AnimeItem(source="yuc", title_cn="测试番剧")]
        result = search_anime_items(items, "   ")
        assert result.ok is False
        assert result.error_type == "invalid_params"

    def test_empty_items_list(self):
        result = search_anime_items([], "测试")
        assert result.ok is True
        assert len(result.data) == 0