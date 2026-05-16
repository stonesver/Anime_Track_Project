"""Search functionality for anime items."""

from anime_parser.errors import invalid_params_diag, not_found_diag
from anime_parser.models import AnimeItem, AnimeParseResult
from anime_parser.normalizers import normalize_title_for_match


def search_anime_items(
    items: list[AnimeItem],
    query: str,
    limit: int = 5,
) -> AnimeParseResult[list[AnimeItem]]:
    """Search anime items by query with confidence scoring."""
    operation = "search_anime_items"
    diagnostics = []

    # Validate query
    if not query or not query.strip():
        return AnimeParseResult(
            ok=False,
            operation=operation,
            error_type="invalid_params",
            error_message="Query cannot be empty",
            diagnostics=[invalid_params_diag("Query cannot be empty")],
        )

    query_normalized = normalize_title_for_match(query)

    # Build candidate list with confidence scores
    candidates: list[tuple[float, int, AnimeItem]] = []

    for item in items:
        confidence = _calculate_confidence(item, query, query_normalized)
        if confidence > 0:
            candidates.append((confidence, len(item.title_cn or ""), item))

    # Sort by confidence (desc), then by title length (asc)
    candidates.sort(key=lambda x: (-x[0], x[1]))

    # Apply limit
    results = [item for _, _, item in candidates[:limit]]

    if not results:
        return AnimeParseResult(
            ok=True,
            operation=operation,
            data=[],
            diagnostics=[not_found_diag(query)],
        )

    return AnimeParseResult(
        ok=True,
        operation=operation,
        data=results,
        diagnostics=diagnostics,
    )


def _calculate_confidence(
    item: AnimeItem,
    query: str,
    query_normalized: str,
) -> float:
    """Calculate match confidence between query and anime item."""
    # Exact match on standard title cn
    if item.title_cn and query.strip() == item.title_cn.strip():
        return 1.0

    # Exact match on other titles
    for title_field in [item.title_jp, item.title_en]:
        if title_field and query.strip() == title_field.strip():
            return 0.95

    # Alias exact match
    for alias in item.aliases:
        if query.strip() == alias.strip():
            return 0.95

    # Title contains match (cn)
    if item.title_cn and query.strip() in item.title_cn.strip():
        return 0.85

    # Title contains match (jp/en)
    for title_field in [item.title_jp, item.title_en]:
        if title_field and query.strip() in title_field.strip():
            return 0.85

    # Alias contains match
    for alias in item.aliases:
        if query.strip() in alias.strip():
            return 0.8

    # Normalized match
    item_normalized = _get_normalized_title(item)
    if item_normalized and query_normalized in item_normalized:
        return 0.7

    # Check if query normalized is contained in item normalized
    if item_normalized and item_normalized in query_normalized:
        return 0.6

    return 0.0


def _get_normalized_title(item: AnimeItem) -> str:
    """Get normalized title for matching."""
    # Prefer Chinese title
    title = item.title_cn or item.title_jp or item.title_en or ""
    return normalize_title_for_match(title)