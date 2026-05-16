"""Tests for yuc-scraper service layer."""

import pytest

from yuc_scraper.errors import ErrorType
from yuc_scraper.service import is_valid_weekday, normalize_season_input, YucService


class MockYucHttpClient:
    """Mock client for testing without network."""

    def __init__(self, fixture_content: str = "", error_type: str = None):
        self.fixture_content = fixture_content
        self.error_type = error_type
        self.fetched_urls = []

    def fetch_home(self):
        if self.error_type:
            from yuc_scraper.models import YucFetchResult
            return YucFetchResult(
                ok=False,
                error_type=self.error_type,
                error_message=f"Mock {self.error_type}",
                source_url="https://yuc.wiki/",
            )
        from yuc_scraper.models import YucFetchResult
        return YucFetchResult(
            ok=True,
            content=self.fixture_content,
            status_code=200,
            source_url="https://yuc.wiki/",
        )

    def fetch_season_page(self, season_compact: str):
        self.fetched_urls.append(season_compact)
        if self.error_type:
            from yuc_scraper.models import YucFetchResult
            return YucFetchResult(
                ok=False,
                error_type=self.error_type,
                error_message=f"Mock {self.error_type}",
                source_url=f"https://yuc.wiki/{season_compact}/",
            )
        from yuc_scraper.models import YucFetchResult
        return YucFetchResult(
            ok=True,
            content=self.fixture_content,
            status_code=200,
            source_url=f"https://yuc.wiki/{season_compact}/",
        )


class TestIsValidWeekday:
    def test_valid_weekdays(self):
        assert is_valid_weekday(None) is True
        assert is_valid_weekday(1) is True
        assert is_valid_weekday(7) is True

    def test_invalid_weekdays(self):
        assert is_valid_weekday(0) is False
        assert is_valid_weekday(8) is False
        assert is_valid_weekday(-1) is False


class TestNormalizeSeasonInput:
    def test_current(self):
        assert normalize_season_input("current") == "current"

    def test_yyyy_mm_format(self):
        assert normalize_season_input("2026-04") == "2026-04"
        assert normalize_season_input("2025-10") == "2025-10"

    def test_yyyymm_format(self):
        assert normalize_season_input("202604") == "2026-04"
        assert normalize_season_input("202510") == "2025-10"

    def test_invalid_format(self):
        with pytest.raises(ValueError):
            normalize_season_input("invalid")
        with pytest.raises(ValueError):
            normalize_season_input("2026")


class TestYucServiceGetCurrentSeason:
    def test_fetch_home_success(self):
        """Test successful home page fetch."""
        import os
        fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "home.html")
        with open(fixture_path, "r", encoding="utf-8") as f:
            html = f.read()

        client = MockYucHttpClient(fixture_content=html)
        service = YucService(client=client)

        result = service.get_current_season()
        assert result.ok is True
        assert "season" in result.data

    def test_fetch_home_network_error(self):
        """Test network error handling."""
        client = MockYucHttpClient(error_type=ErrorType.NETWORK_ERROR)
        service = YucService(client=client)

        result = service.get_current_season()
        assert result.ok is False
        assert result.error_type == ErrorType.NETWORK_ERROR

    def test_fetch_home_timeout(self):
        """Test timeout handling."""
        client = MockYucHttpClient(error_type=ErrorType.NETWORK_TIMEOUT)
        service = YucService(client=client)

        result = service.get_current_season()
        assert result.ok is False
        assert result.error_type == ErrorType.NETWORK_TIMEOUT


class TestYucServiceGetWeeklySchedule:
    def test_invalid_weekday(self):
        """Test invalid weekday parameter."""
        client = MockYucHttpClient()
        service = YucService(client=client)

        result = service.get_weekly_schedule(season="2026-04", weekday=8)
        assert result.ok is False
        assert result.error_type == ErrorType.INVALID_PARAMS

    def test_season_page_fetch(self):
        """Test season page is fetched."""
        import os
        fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "season_202604.html")
        with open(fixture_path, "r", encoding="utf-8") as f:
            html = f.read()

        client = MockYucHttpClient(fixture_content=html)
        service = YucService(client=client)

        result = service.get_weekly_schedule(season="2026-04", weekday=None)
        # Season page should be fetched
        assert "202604" in client.fetched_urls


class TestYucServiceSearch:
    def test_empty_query(self):
        """Test empty query returns invalid_params."""
        client = MockYucHttpClient()
        service = YucService(client=client)

        result = service.search_anime(query="   ", season="2026-04")
        assert result.ok is False
        assert result.error_type == ErrorType.INVALID_PARAMS

    def test_invalid_limit(self):
        """Test invalid limit returns invalid_params."""
        client = MockYucHttpClient()
        service = YucService(client=client)

        result = service.search_anime(query="test", season="2026-04", limit=0)
        assert result.ok is False
        assert result.error_type == ErrorType.INVALID_PARAMS

        result = service.search_anime(query="test", season="2026-04", limit=51)
        assert result.ok is False
        assert result.error_type == ErrorType.INVALID_PARAMS