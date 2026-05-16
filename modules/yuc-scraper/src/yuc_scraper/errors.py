"""Error types and diagnostic utilities for yuc-scraper."""

from typing import Optional


class ErrorType:
    """Error type constants for yuc scraper."""

    NETWORK_TIMEOUT = "network_timeout"
    NETWORK_ERROR = "network_error"
    HTTP_ERROR = "http_error"
    SOURCE_UNAVAILABLE = "source_unavailable"
    INVALID_PARAMS = "invalid_params"
    PARSE_ZERO_ITEMS = "parse_zero_items"
    PARSE_SCHEMA_CHANGED = "parse_schema_changed"
    AMBIGUOUS_MATCH = "ambiguous_match"
    NOT_FOUND = "not_found"


def network_timeout_diag(message: str = "Request timed out") -> dict:
    """Create diagnostic for network timeout."""
    return {
        "code": ErrorType.NETWORK_TIMEOUT,
        "message": message,
        "severity": "error",
    }


def network_error_diag(message: str = "Network connection failed") -> dict:
    """Create diagnostic for network error."""
    return {
        "code": ErrorType.NETWORK_ERROR,
        "message": message,
        "severity": "error",
    }


def http_error_diag(status_code: int, message: Optional[str] = None) -> dict:
    """Create diagnostic for HTTP error."""
    return {
        "code": ErrorType.HTTP_ERROR,
        "message": message or f"HTTP {status_code}",
        "severity": "error",
    }


def source_unavailable_diag(message: str = "Source page returned empty or invalid content") -> dict:
    """Create diagnostic for source unavailable."""
    return {
        "code": ErrorType.SOURCE_UNAVAILABLE,
        "message": message,
        "severity": "error",
    }


def invalid_params_diag(message: str) -> dict:
    """Create diagnostic for invalid parameters."""
    return {
        "code": ErrorType.INVALID_PARAMS,
        "message": message,
        "severity": "error",
    }


def parse_zero_items_diag(message: str = "HTML returned 200 but no schedule items were parsed") -> dict:
    """Create diagnostic for parse zero items."""
    return {
        "code": ErrorType.PARSE_ZERO_ITEMS,
        "message": message,
        "severity": "error",
    }


def parse_schema_changed_diag(message: str = "Critical selector failed - page structure may have changed") -> dict:
    """Create diagnostic for schema changed."""
    return {
        "code": ErrorType.PARSE_SCHEMA_CHANGED,
        "message": message,
        "severity": "error",
    }


def ambiguous_match_diag(message: str = "Ambiguous match, returning candidates") -> dict:
    """Create diagnostic for ambiguous match."""
    return {
        "code": ErrorType.AMBIGUOUS_MATCH,
        "message": message,
        "severity": "info",
    }


def not_found_diag(message: str) -> dict:
    """Create diagnostic for not found."""
    return {
        "code": ErrorType.NOT_FOUND,
        "message": message,
        "severity": "info",
    }