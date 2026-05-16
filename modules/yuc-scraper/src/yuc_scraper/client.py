"""HTTP client for yuc.wiki."""

from typing import Optional

import httpx

from yuc_scraper.errors import (
    ErrorType,
    http_error_diag,
    network_error_diag,
    network_timeout_diag,
    source_unavailable_diag,
)
from yuc_scraper.models import YucFetchResult


class YucHttpClient:
    """HTTP client for fetching yuc.wiki pages."""

    DEFAULT_TIMEOUT = 10.0
    DEFAULT_USER_AGENT = "AnimeCode/yuc-scraper v0.1"

    def __init__(
        self,
        base_url: str = "https://yuc.wiki",
        timeout: float = DEFAULT_TIMEOUT,
        user_agent: str = DEFAULT_USER_AGENT,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.user_agent = user_agent
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        """Lazy-create httpx client."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent},
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def fetch_home(self) -> YucFetchResult:
        """Fetch the yuc home page."""
        return self.fetch_url(f"{self.base_url}/")

    def fetch_season_page(self, season_compact: str) -> YucFetchResult:
        """Fetch a season page by compact format (YYYYMM)."""
        url = f"{self.base_url}/{season_compact}/"
        return self.fetch_url(url)

    def fetch_url(self, url: str) -> YucFetchResult:
        """Fetch a URL and return structured result."""
        try:
            response = self.client.get(url, timeout=self.timeout)
            return self._handle_response(response, url)
        except httpx.TimeoutException:
            return YucFetchResult(
                ok=False,
                error_type=ErrorType.NETWORK_TIMEOUT,
                error_message="Request timed out",
                source_url=url,
            )
        except httpx.ConnectError as e:
            return YucFetchResult(
                ok=False,
                error_type=ErrorType.NETWORK_ERROR,
                error_message=f"Connection failed: {e}",
                source_url=url,
            )
        except httpx.TLSError as e:
            return YucFetchResult(
                ok=False,
                error_type=ErrorType.NETWORK_ERROR,
                error_message=f"TLS error: {e}",
                source_url=url,
            )
        except Exception as e:
            return YucFetchResult(
                ok=False,
                error_type=ErrorType.NETWORK_ERROR,
                error_message=str(e),
                source_url=url,
            )

    def _handle_response(self, response: httpx.Response, url: str) -> YucFetchResult:
        """Handle HTTP response and map to structured result."""
        if response.status_code != 200:
            return YucFetchResult(
                ok=False,
                status_code=response.status_code,
                error_type=ErrorType.HTTP_ERROR,
                error_message=f"HTTP {response.status_code}",
                source_url=url,
            )

        content = response.text
        if not content or len(content.strip()) == 0:
            return YucFetchResult(
                ok=False,
                status_code=response.status_code,
                error_type=ErrorType.SOURCE_UNAVAILABLE,
                error_message="Empty response",
                source_url=url,
            )

        return YucFetchResult(
            ok=True,
            content=content,
            status_code=response.status_code,
            source_url=url,
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()