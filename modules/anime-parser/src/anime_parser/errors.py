"""Error types and diagnostic utilities."""

from typing import Any

from anime_parser.models import Diagnostic


class ErrorType:
    """Error type constants."""

    INVALID_SOURCE_RECORD = "invalid_source_record"
    MISSING_TITLE = "missing_title"
    INVALID_SEASON = "invalid_season"
    INVALID_WEEKDAY = "invalid_weekday"
    INVALID_DATE = "invalid_date"
    INVALID_TIME = "invalid_time"
    INVALID_URL = "invalid_url"
    MERGE_CONFLICT = "merge_conflict"
    AMBIGUOUS_MATCH = "ambiguous_match"
    NOT_FOUND = "not_found"
    INVALID_PARAMS = "invalid_params"
    PARSE_ZERO_ITEMS = "parse_zero_items"


def create_diagnostic(
    code: str,
    message: str,
    field: str | None = None,
    raw_value: Any = None,
    severity: str = "info",
) -> Diagnostic:
    """Create a diagnostic instance."""
    return Diagnostic(
        code=code,
        field=field,
        message=message,
        raw_value=raw_value,
        severity=severity,
    )


def invalid_source_record_diag(
    message: str,
    raw_value: Any = None,
) -> Diagnostic:
    """Create diagnostic for invalid source record."""
    return create_diagnostic(
        code=ErrorType.INVALID_SOURCE_RECORD,
        message=message,
        raw_value=raw_value,
        severity="error",
    )


def missing_title_diag(raw_value: Any = None) -> Diagnostic:
    """Create diagnostic for missing title."""
    return create_diagnostic(
        code=ErrorType.MISSING_TITLE,
        message="Title is required to generate AnimeItem",
        raw_value=raw_value,
        severity="error",
    )


def invalid_season_diag(
    raw_value: str | None,
    message: str = "Cannot normalize season",
) -> Diagnostic:
    """Create diagnostic for invalid season."""
    return create_diagnostic(
        code=ErrorType.INVALID_SEASON,
        message=message,
        field="season_raw",
        raw_value=raw_value,
        severity="error",
    )


def invalid_weekday_diag(
    raw_value: str | int | None,
    message: str = "Cannot normalize weekday",
) -> Diagnostic:
    """Create diagnostic for invalid weekday."""
    return create_diagnostic(
        code=ErrorType.INVALID_WEEKDAY,
        message=message,
        field="weekday_raw",
        raw_value=raw_value,
        severity="warning",
    )


def invalid_date_diag(
    raw_value: str | None,
    message: str = "Cannot normalize start date",
) -> Diagnostic:
    """Create diagnostic for invalid date."""
    return create_diagnostic(
        code=ErrorType.INVALID_DATE,
        message=message,
        field="start_date_raw",
        raw_value=raw_value,
        severity="warning",
    )


def invalid_time_diag(
    raw_value: str | None,
    message: str = "Cannot normalize air time",
) -> Diagnostic:
    """Create diagnostic for invalid time."""
    return create_diagnostic(
        code=ErrorType.INVALID_TIME,
        message=message,
        field="air_time_raw",
        raw_value=raw_value,
        severity="info",
    )


def invalid_url_diag(
    raw_value: str | None,
    message: str = "Invalid URL",
) -> Diagnostic:
    """Create diagnostic for invalid URL."""
    return create_diagnostic(
        code=ErrorType.INVALID_URL,
        message=message,
        raw_value=raw_value,
        severity="warning",
    )


def merge_conflict_diag(
    field: str,
    value1: Any,
    value2: Any,
) -> Diagnostic:
    """Create diagnostic for merge conflict."""
    return create_diagnostic(
        code=ErrorType.MERGE_CONFLICT,
        message=f"Conflict on field '{field}': '{value1}' vs '{value2}'",
        field=field,
        raw_value={"value1": value1, "value2": value2},
        severity="warning",
    )


def ambiguous_match_diag(
    message: str = "Ambiguous match, returning candidates",
) -> Diagnostic:
    """Create diagnostic for ambiguous match."""
    return create_diagnostic(
        code=ErrorType.AMBIGUOUS_MATCH,
        message=message,
        severity="info",
    )


def parse_zero_items_diag() -> Diagnostic:
    """Create diagnostic for parsing zero items."""
    return create_diagnostic(
        code=ErrorType.PARSE_ZERO_ITEMS,
        message="All records failed to parse",
        severity="error",
    )


def not_found_diag(query: str) -> Diagnostic:
    """Create diagnostic for not found."""
    return create_diagnostic(
        code=ErrorType.NOT_FOUND,
        message=f"No match found for query: {query}",
        severity="info",
    )


def invalid_params_diag(message: str) -> Diagnostic:
    """Create diagnostic for invalid parameters."""
    return create_diagnostic(
        code=ErrorType.INVALID_PARAMS,
        message=message,
        severity="error",
    )