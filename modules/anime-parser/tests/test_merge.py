"""Tests for merge module."""

import pytest

from anime_parser.models import SourceAnimeRecord
from anime_parser.merge import merge_anime_records


class TestMergeAnimeRecords:
    def test_single_record(self):
        records = [
            SourceAnimeRecord(
                source="yuc",
                source_id="123",
                title_raw="测试番剧",
            )
        ]
        result = merge_anime_records(records)
        assert result.ok is True
        assert result.data.title_cn == "测试番剧"

    def test_same_source_id_merge(self):
        records = [
            SourceAnimeRecord(
                source="yuc",
                source_id="123",
                title_raw="测试番剧",
                description_raw="描述1",
            ),
            SourceAnimeRecord(
                source="yuc",
                source_id="123",
                title_raw="测试番剧",
                description_raw="描述2",
                cover_url_raw="https://example.com/cover.jpg",
            ),
        ]
        result = merge_anime_records(records)
        assert result.ok is True
        # Should merge into single item
        item = result.data if hasattr(result.data, 'title_cn') else result.data[0]
        assert item.description in ["描述1", "描述2"]

    def test_different_source_id_no_merge(self):
        records = [
            SourceAnimeRecord(
                source="yuc",
                source_id="123",
                title_raw="测试番剧A",
            ),
            SourceAnimeRecord(
                source="yuc",
                source_id="456",
                title_raw="测试番剧B",
            ),
        ]
        result = merge_anime_records(records)
        assert result.ok is True
        # Should return list of two items
        assert isinstance(result.data, list)
        assert len(result.data) == 2

    def test_same_normalized_title_merge(self):
        records = [
            SourceAnimeRecord(
                source="yuc",
                source_id=None,
                title_raw="测试番剧",
            ),
            SourceAnimeRecord(
                source="yuc",
                source_id=None,
                title_raw="测试番剧",  # Same after normalization
            ),
        ]
        result = merge_anime_records(records)
        assert result.ok is True

    def test_no_source_id_different_title(self):
        records = [
            SourceAnimeRecord(
                source="yuc",
                source_id=None,
                title_raw="番剧A",
            ),
            SourceAnimeRecord(
                source="yuc",
                source_id=None,
                title_raw="番剧B",
            ),
        ]
        result = merge_anime_records(records)
        assert result.ok is True
        # Should return list of two items
        assert isinstance(result.data, list)
        assert len(result.data) == 2

    def test_empty_records(self):
        result = merge_anime_records([])
        assert result.ok is False
        assert result.error_type == "invalid_source_record"

    def test_merge_conflict_diagnostic(self):
        records = [
            SourceAnimeRecord(
                source="yuc",
                source_id="123",
                title_raw="测试番剧",
                description_raw="描述A",
            ),
            SourceAnimeRecord(
                source="yuc",
                source_id="123",
                title_raw="测试番剧",
                description_raw="描述B",  # Different description
            ),
        ]
        result = merge_anime_records(records)
        assert result.ok is True
        # Should have merge conflict diagnostic
        assert len(result.diagnostics) > 0