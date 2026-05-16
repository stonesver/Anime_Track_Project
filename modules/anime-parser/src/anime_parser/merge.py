"""Merge functionality for combining anime records."""

from typing import Dict, List, Optional, Tuple, Union

from anime_parser.errors import merge_conflict_diag
from anime_parser.models import AnimeItem, AnimeParseResult, SourceAnimeRecord
from anime_parser.normalizers import normalize_title_for_match


def merge_anime_records(
    records: List[SourceAnimeRecord],
) -> AnimeParseResult:
    """Merge multiple source records into one or more AnimeItems."""
    operation = "merge_anime_records"
    diagnostics = []

    if not records:
        return AnimeParseResult(
            ok=False,
            operation=operation,
            error_type="invalid_source_record",
            error_message="No records to merge",
            diagnostics=[],
        )

    # Group records by source_id first (strongest merge signal)
    by_source_id: Dict[str, List[SourceAnimeRecord]] = {}
    no_source_id: List[SourceAnimeRecord] = []

    for record in records:
        if record.source_id:
            key = f"{record.source}:{record.source_id}"
            if key not in by_source_id:
                by_source_id[key] = []
            by_source_id[key].append(record)
        else:
            no_source_id.append(record)

    # Merge records with same source_id
    merged_items: List[AnimeItem] = []

    for key, recs in by_source_id.items():
        # All records with same source_id should merge
        merged, merge_diags = _merge_records_list(recs)
        merged_items.append(merged)
        diagnostics.extend(merge_diags)

    # For records without source_id, check normalized title match
    title_groups: Dict[str, List[SourceAnimeRecord]] = {}

    for record in no_source_id:
        title = _get_primary_title(record)
        norm_title = normalize_title_for_match(title)
        if norm_title:
            # Check if we have an existing group with same normalized title
            found = False
            for existing_norm, group in title_groups.items():
                if norm_title == existing_norm:
                    group.append(record)
                    found = True
                    break
                # Also check for high similarity
                if _titles_are_similar(norm_title, existing_norm):
                    group.append(record)
                    found = True
                    break
            if not found:
                title_groups[norm_title] = [record]

    # Merge each title group
    for norm_title, recs in title_groups.items():
        if len(recs) == 1:
            # Single record, just normalize
            from anime_parser.service import normalize_anime
            result = normalize_anime(recs[0])
            if result.ok and result.data:
                merged_items.append(result.data)
                diagnostics.extend(result.diagnostics)
        else:
            # Multiple records with similar title - merge
            merged, merge_diags = _merge_records_list(recs)
            merged_items.append(merged)
            diagnostics.extend(merge_diags)

    # Check if we have ambiguous matches (multiple items with similar titles)
    if len(merged_items) > 1:
        # Check for title similarity
        ambiguous = _check_ambiguous(merged_items)
        if ambiguous:
            from anime_parser.errors import ambiguous_match_diag
            diagnostics.append(ambiguous_match_diag(
                f"Multiple potential matches found, returning {len(merged_items)} candidates"
            ))
            return AnimeParseResult(
                ok=True,
                operation=operation,
                data=merged_items,
                diagnostics=diagnostics,
            )

    return AnimeParseResult(
        ok=True,
        operation=operation,
        data=merged_items[0] if len(merged_items) == 1 else merged_items,
        diagnostics=diagnostics,
    )


def _merge_records_list(records: List[SourceAnimeRecord]) -> Tuple[AnimeItem, List]:
    """Merge a list of source records into a single AnimeItem."""
    from anime_parser.service import normalize_anime

    diagnostics = []

    if not records:
        raise ValueError("Cannot merge empty records list")

    if len(records) == 1:
        result = normalize_anime(records[0])
        return result.data, result.diagnostics

    # Normalize all records
    items = []
    for record in records:
        result = normalize_anime(record)
        if result.ok and result.data:
            items.append(result.data)

    if not items:
        raise ValueError("No records could be normalized")

    # Merge items
    merged = items[0]
    for item in items[1:]:
        merged, merge_diags = _merge_anime_items(merged, item)
        diagnostics.extend(merge_diags)

    return merged, diagnostics


def _merge_anime_items(item1: AnimeItem, item2: AnimeItem) -> Tuple[AnimeItem, List]:
    """Merge two AnimeItems, preferring non-empty and longer values."""
    diagnostics = []
    result = item1.model_copy(deep=True)

    # Merge fields, preferring non-empty and longer values
    fields_to_merge = [
        ("title_cn", lambda a, b: _prefer_longer(a, b)),
        ("title_jp", lambda a, b: _prefer_longer(a, b)),
        ("title_en", lambda a, b: _prefer_longer(a, b)),
        ("aliases", lambda a, b: list(set((a or []) + (b or [])))),
        ("description", lambda a, b: _prefer_longer(a, b)),
        ("cover_url", lambda a, b: a or b),
        ("official_url", lambda a, b: a or b),
        ("platform_links", lambda a, b: a or b),
    ]

    for field_name, merge_func in fields_to_merge:
        val1 = getattr(item1, field_name, None)
        val2 = getattr(item2, field_name, None)
        if val1 != val2:
            merged_val = merge_func(val1, val2)
            setattr(result, field_name, merged_val)
            if val1 and val2 and merged_val == val1:
                # Conflict resolved but both had values
                diagnostics.append(merge_conflict_diag(field_name, val1, val2))

    # Keep the higher confidence
    result.confidence = max(item1.confidence, item2.confidence)

    return result, diagnostics


def _prefer_longer(a: Optional[str], b: Optional[str]) -> Optional[str]:
    """Prefer non-empty and longer value."""
    if not a:
        return b
    if not b:
        return a
    return a if len(a) >= len(b) else b


def _get_primary_title(record: SourceAnimeRecord) -> str:
    """Get primary title from source record."""
    return (record.title_cn_raw or record.title_raw or record.title_jp_raw or record.title_en_raw or "").strip()


def _titles_are_similar(norm1: str, norm2: str) -> bool:
    """Check if two normalized titles are similar enough to merge."""
    if not norm1 or not norm2:
        return False

    # Exact match
    if norm1 == norm2:
        return True

    # One contains the other
    if len(norm1) > 3 and len(norm2) > 3:
        if norm1 in norm2 or norm2 in norm1:
            return True

    # Levenshtein distance for short titles (simple implementation)
    # This is a simplified version - V1 doesn't use external libraries
    if abs(len(norm1) - len(norm2)) <= 2:
        # Simple check: if they share most characters
        common = sum(1 for c in norm1 if c in norm2)
        total = max(len(norm1), len(norm2))
        if total > 0 and common / total >= 0.8:
            return True

    return False


def _check_ambiguous(items: List[AnimeItem]) -> bool:
    """Check if there are ambiguous matches among items."""
    if len(items) <= 1:
        return False

    titles = []
    for item in items:
        title = item.title_cn or item.title_jp or item.title_en or ""
        if title:
            titles.append(normalize_title_for_match(title))

    # Check if any titles are similar
    for i, t1 in enumerate(titles):
        for t2 in titles[i+1:]:
            if _titles_are_similar(t1, t2):
                return True

    return False