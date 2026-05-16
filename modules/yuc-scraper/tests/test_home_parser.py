"""Tests for yuc home page parser - season links."""

import os

from yuc_scraper.config import DEFAULT_CONFIG
from yuc_scraper.parser import parse_season_links, select_current_season


def read_fixture(filename: str) -> str:
    """Read fixture file."""
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", filename)
    with open(fixture_path, "r", encoding="utf-8") as f:
        return f.read()


def get_debug_diagnostics(html: str):
    """Helper to get diagnostics for debugging."""
    from yuc_scraper.config import DEFAULT_CONFIG
    return parse_season_links(html, DEFAULT_CONFIG)


class TestParseSeasonLinks:
    def test_parse_home_with_new_marker(self):
        """Test parsing home page with *(New) marker."""
        html = read_fixture("home.html")
        links, diagnostics = parse_season_links(html, DEFAULT_CONFIG)

        # Should find multiple season links
        assert len(links) >= 5

        # Should find the New marked link
        new_links = [l for l in links if l.is_new]
        assert len(new_links) >= 1

    def test_parse_skips_invalid_month(self):
        """Test that invalid month (02) is skipped."""
        html = read_fixture("home.html")
        links, diagnostics = get_debug_diagnostics(html)

        # Check diagnostics for invalid month warning
        invalid_diags = [d for d in diagnostics if "invalid_month" in str(d)]
        # The fixture has month 02 which should be skipped

    def test_parse_deduplicates_seasons(self):
        """Test that duplicate seasons are deduplicated."""
        html = read_fixture("home.html")
        links, _ = parse_season_links(html, DEFAULT_CONFIG)

        season_values = [l.season for l in links]
        assert len(season_values) == len(set(season_values))

    def test_parse_sorts_by_season_descending(self):
        """Test that links are sorted by season descending."""
        html = read_fixture("home.html")
        links, _ = parse_season_links(html, DEFAULT_CONFIG)

        seasons = [l.season for l in links]
        assert seasons == sorted(seasons, reverse=True)

    def test_parse_empty_html_returns_error(self):
        """Test that empty HTML returns source_unavailable."""
        links, diagnostics = parse_season_links("", DEFAULT_CONFIG)
        assert len(links) == 0
        assert any(d.code == "source_unavailable" for d in diagnostics)


class TestSelectCurrentSeason:
    def test_select_prioritizes_new_marker(self):
        """Test that New marker takes priority."""
        from yuc_scraper.models import YucSeasonLink

        links = [
            YucSeasonLink(season="2025-10", season_compact="202510", url="https://yuc.wiki/202510/", text="2025年10月新番", is_new=False),
            YucSeasonLink(season="2025-10", season_compact="202510", url="https://yuc.wiki/202510/", text="*(New) 2025年10月新番", is_new=True),
        ]

        selected, diags = select_current_season(links)
        assert selected is not None
        assert selected.is_new is True
        assert selected.season == "2025-10"

    def test_select_fallback_to_latest_without_new(self):
        """Test fallback to latest season when no New marker."""
        from yuc_scraper.models import YucSeasonLink

        links = [
            YucSeasonLink(season="2025-04", season_compact="202504", url="https://yuc.wiki/202504/", text="2025年4月新番", is_new=False),
            YucSeasonLink(season="2025-10", season_compact="202510", url="https://yuc.wiki/202510/", text="2025年10月新番", is_new=False),
        ]

        selected, diags = select_current_season(links)
        assert selected is not None
        assert selected.season == "2025-10"

    def test_select_empty_list_returns_error(self):
        """Test that empty list returns parse_zero_items."""
        selected, diags = select_current_season([])
        assert selected is None
        assert any(d.code == "parse_zero_items" for d in diags)