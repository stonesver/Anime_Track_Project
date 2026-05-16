"""Adapters from yuc source records to anime-parser source records."""

import re
from typing import Iterable, Optional
from urllib.parse import urljoin

from anime_parser.models import SourceAnimeRecord, SourcePlatformLink
from anime_parser.normalizers import normalize_title_for_match

from yuc_scraper.models import YucDetailSourceRecord, YucWeeklySourceRecord


def yuc_records_to_source_records(
    weekly_records: Iterable[YucWeeklySourceRecord],
    detail_records: Iterable[YucDetailSourceRecord],
) -> list[SourceAnimeRecord]:
    """Convert parsed yuc weekly records to anime-parser source records."""
    detail_index = _build_detail_index(detail_records)
    source_records = []
    for record in weekly_records:
        detail = _match_detail(record, detail_index)
        source_records.append(yuc_weekly_record_to_source_record(record, detail))
    return source_records


def yuc_weekly_record_to_source_record(
    record: YucWeeklySourceRecord,
    detail: Optional[YucDetailSourceRecord] = None,
) -> SourceAnimeRecord:
    """Convert one yuc weekly source record to the shared anime-parser shape."""
    aliases = _title_aliases(record.title_text, record.title_cn)
    if detail:
        aliases.extend(_title_aliases(detail.title_text, detail.title_cn))

    return SourceAnimeRecord(
        source="yuc",
        source_url=record.source_url,
        source_id=None,
        season_raw=record.season,
        title_raw=record.title_text,
        title_cn_raw=detail.title_cn if detail and detail.title_cn else record.title_cn,
        title_jp_raw=detail.title_jp if detail else None,
        aliases_raw=_dedupe(aliases),
        weekday_raw=record.weekday_label or record.weekday,
        air_time_raw=record.air_time,
        start_date_raw=record.start_date,
        description_raw=_description_from(record, detail),
        cover_url_raw=_absolute_url(record.cover_url, record.source_url),
        official_url_raw=_absolute_url(detail.official_url, record.source_url) if detail else None,
        platform_links_raw=[
            SourcePlatformLink(
                url=_absolute_url(link.url, record.source_url),
                label=link.label,
                region=link.region,
                kind=link.kind,
            )
            for link in record.platform_links
        ],
        source_payload={
            "weekly_selector_hits": record.selector_hits,
            "detail_selector_hits": detail.selector_hits if detail else {},
            "weekday_label": record.weekday_label,
        },
    )


def _build_detail_index(
    records: Iterable[YucDetailSourceRecord],
) -> dict[str, YucDetailSourceRecord]:
    index = {}
    for record in records:
        for title in _title_aliases(record.title_text, record.title_cn):
            key = normalize_title_for_match(title)
            if key and key not in index:
                index[key] = record
    return index


def _match_detail(
    record: YucWeeklySourceRecord,
    detail_index: dict[str, YucDetailSourceRecord],
) -> Optional[YucDetailSourceRecord]:
    for title in _title_aliases(record.title_text, record.title_cn):
        key = normalize_title_for_match(title)
        if key in detail_index:
            return detail_index[key]
    return None


def _title_aliases(*values: Optional[str]) -> list[str]:
    aliases = []
    for value in values:
        if not value:
            continue
        aliases.append(value)
        aliases.extend(part for part in re.split(r"[\n/／|｜]+", value) if part.strip())
    return _dedupe(aliases)


def _description_from(
    record: YucWeeklySourceRecord,
    detail: Optional[YucDetailSourceRecord],
) -> Optional[str]:
    parts = []
    if record.note:
        parts.append(record.note)
    if detail and detail.broadcast_text:
        parts.append(detail.broadcast_text)
    return "；".join(_dedupe(parts)) or None


def _absolute_url(value: Optional[str], base_url: str) -> Optional[str]:
    if not value:
        return None
    if value.startswith("//"):
        return f"https:{value}"
    return urljoin(base_url, value)


def _dedupe(values: Iterable[Optional[str]]) -> list[str]:
    seen = set()
    deduped = []
    for value in values:
        if value is None:
            continue
        cleaned = re.sub(r"\s+", " ", value).strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        deduped.append(cleaned)
    return deduped
