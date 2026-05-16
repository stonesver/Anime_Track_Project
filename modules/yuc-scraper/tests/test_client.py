"""Tests for yuc-scraper client."""

import pytest

from yuc_scraper.client import YucHttpClient
from yuc_scraper.errors import ErrorType
from yuc_scraper.models import YucFetchResult


class TestYucHttpClient:
    def test_client_initialization(self):
        client = YucHttpClient()
        assert client.base_url == "https://yuc.wiki"
        assert client.timeout == 10.0
        assert "AnimeCode" in client.user_agent

    def test_client_custom_params(self):
        client = YucHttpClient(base_url="https://test.com", timeout=5.0)
        assert client.base_url == "https://test.com"
        assert client.timeout == 5.0

    def test_client_context_manager(self):
        with YucHttpClient() as client:
            assert client.client is not None
        # Should be closed after context exit


class TestYucFetchResult:
    def test_successful_result(self):
        result = YucFetchResult(
            ok=True,
            content="<html>test</html>",
            status_code=200,
            source_url="https://yuc.wiki/",
        )
        assert result.ok is True
        assert result.content == "<html>test</html>"
        assert result.status_code == 200

    def test_error_result_network_timeout(self):
        result = YucFetchResult(
            ok=False,
            error_type=ErrorType.NETWORK_TIMEOUT,
            error_message="Request timed out",
            source_url="https://yuc.wiki/",
        )
        assert result.ok is False
        assert result.error_type == ErrorType.NETWORK_TIMEOUT

    def test_error_result_network_error(self):
        result = YucFetchResult(
            ok=False,
            error_type=ErrorType.NETWORK_ERROR,
            error_message="Connection failed",
            source_url="https://yuc.wiki/",
        )
        assert result.ok is False
        assert result.error_type == ErrorType.NETWORK_ERROR

    def test_error_result_http_error(self):
        result = YucFetchResult(
            ok=False,
            error_type=ErrorType.HTTP_ERROR,
            error_message="HTTP 404",
            status_code=404,
            source_url="https://yuc.wiki/404/",
        )
        assert result.ok is False
        assert result.error_type == ErrorType.HTTP_ERROR
        assert result.status_code == 404