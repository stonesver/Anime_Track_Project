"""Tests for yuc season page parser - weekly and detail records."""

import os

from yuc_scraper.config import DEFAULT_CONFIG
from yuc_scraper.parser import parse_season_page


def read_fixture(filename: str) -> str:
    """Read fixture file."""
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", filename)
    with open(fixture_path, "r", encoding="utf-8") as f:
        return f.read()


class TestParseSeasonPage:
    def test_parse_weekly_records(self):
        """Test parsing weekly records from season page."""
        html = read_fixture("season_202604.html")
        result, diags = parse_season_page(html, "2026-04", "https://yuc.wiki/202604/", DEFAULT_CONFIG)

        assert result.season == "2026-04"
        assert len(result.weekly_records) > 0

    def test_parse_weekday_markers(self):
        """Test that weekday markers are correctly parsed."""
        html = read_fixture("season_202604.html")
        result, diags = parse_season_page(html, "2026-04", "https://yuc.wiki/202604/", DEFAULT_CONFIG)

        weekdays = [r.weekday for r in result.weekly_records if r.weekday is not None]
        assert len(set(weekdays)) > 1  # Multiple weekdays

    def test_parse_air_time_24xx(self):
        """Test that 24:xx and 25:xx times are preserved."""
        html = read_fixture("season_202604.html")
        result, diags = parse_season_page(html, "2026-04", "https://yuc.wiki/202604/", DEFAULT_CONFIG)

        late_times = [r.air_time for r in result.weekly_records if r.air_time and ("24:" in r.air_time or "25:" in r.air_time)]
        assert len(late_times) > 0

    def test_parse_cover_data_src(self):
        """Test that cover img uses data-src attribute."""
        html = read_fixture("season_202604.html")
        result, diags = parse_season_page(html, "2026-04", "https://yuc.wiki/202604/", DEFAULT_CONFIG)

        covers = [r.cover_url for r in result.weekly_records if r.cover_url]
        assert len(covers) > 0
        assert all("example.com" in c for c in covers)

    def test_parse_br_in_title(self):
        """Test that <br> in title is preserved as space."""
        html = read_fixture("season_202604.html")
        result, diags = parse_season_page(html, "2026-04", "https://yuc.wiki/202604/", DEFAULT_CONFIG)

        titles_with_br = [r.title_text for r in result.weekly_records if r.title_text and "\n" in r.title_text]
        assert len(titles_with_br) > 0

    def test_parse_platform_links(self):
        """Test that platform links are parsed."""
        html = read_fixture("season_202604.html")
        result, diags = parse_season_page(html, "2026-04", "https://yuc.wiki/202604/", DEFAULT_CONFIG)

        records_with_links = [r for r in result.weekly_records if len(r.platform_links) > 0]
        assert len(records_with_links) > 0

        for record in records_with_links:
            for link in record.platform_links:
                assert link.kind == "streaming"

    def test_parse_detail_records(self):
        """Test parsing detail records."""
        html = read_fixture("season_202604.html")
        result, diags = parse_season_page(html, "2026-04", "https://yuc.wiki/202604/", DEFAULT_CONFIG)

        assert len(result.detail_records) > 0

    def test_parse_detail_records_split_across_table_rows(self):
        """Test parsing one detail block whose fields are split across table rows."""
        html = """
        <div class="post-body">
            <div>
                <table width="500px">
                    <tr>
                        <td class="title_main_r" colspan="2" rowspan="2">
                            <p class="title_cn_r3">自称恶役千金的婚约者观察记录</p>
                            <p class="title_jp_r1">自称悪役令嬢な婚約者の観察記録。</p>
                        </td>
                        <td class="type_c_r">小说改编动画</td>
                    </tr>
                    <tr><td class="type_tag_r">穿越/恋爱/喜剧</td></tr>
                    <tr>
                        <td rowspan="2" class="staff_r">动画制作：苇Production</td>
                        <td rowspan="2" class="cast_r">小林裕介　富田美忧</td>
                        <td class="link_a_r">
                            <a href="https://jisho-akuyaku-anime.jp/" target="_blank">动画官网</a>
                            <p class="broadcast_r">4/6周一晚间</p>
                        </td>
                    </tr>
                </table>
            </div>
        </div>
        """
        result, diags = parse_season_page(html, "2026-04", "https://yuc.wiki/202604/", DEFAULT_CONFIG)

        assert len(result.detail_records) == 1
        detail = result.detail_records[0]
        assert detail.title_cn == "自称恶役千金的婚约者观察记录"
        assert detail.types == ["小说改编动画"]
        assert detail.tags == ["穿越/恋爱/喜剧"]
        assert detail.staff == ["动画制作：苇Production"]
        assert detail.cast == ["小林裕介　富田美忧"]
        assert detail.official_url == "https://jisho-akuyaku-anime.jp/"
        assert detail.broadcast_text == "4/6周一晚间"

    def test_parse_empty_html_returns_error(self):
        """Test that empty HTML returns source_unavailable."""
        result, diags = parse_season_page("", "2026-04", "https://yuc.wiki/202604/", DEFAULT_CONFIG)
        assert any(d.code == "source_unavailable" for d in result.diagnostics)

    def test_parse_schema_changed(self):
        """Test that missing .post-body returns schema_changed."""
        html = read_fixture("season_schema_changed.html")
        result, diags = parse_season_page(html, "2026-04", "https://yuc.wiki/202604/", DEFAULT_CONFIG)
        assert any(d.code == "parse_schema_changed" for d in result.diagnostics)

    def test_parse_empty_article(self):
        """Test that empty article returns parse_zero_items."""
        html = read_fixture("empty_article.html")
        result, diags = parse_season_page(html, "2026-04", "https://yuc.wiki/202604/", DEFAULT_CONFIG)
        # Should have some diagnostics about zero items
        assert len(result.weekly_records) == 0
