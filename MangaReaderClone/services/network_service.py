"""Network service for HTTP requests with caching and rate limiting."""

import asyncio
import logging
from typing import Optional
from urllib.parse import urlencode, urljoin, quote

import aiohttp
from yarl import URL

logger = logging.getLogger(__name__)

# Rate limit: max requests per second per domain
RATE_LIMIT = 3
_instance: Optional["NetworkService"] = None


class NetworkService:
    """Singleton HTTP client with connection pooling and rate limiting."""

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._cache: dict[str, tuple[float, any]] = {}
        self._cache_ttl = 300  # 5 minutes

    @classmethod
    def shared(cls) -> "NetworkService":
        global _instance
        if _instance is None:
            _instance = cls()
        return _instance

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    def _get_semaphore(self, domain: str) -> asyncio.Semaphore:
        if domain not in self._semaphores:
            self._semaphores[domain] = asyncio.Semaphore(RATE_LIMIT)
        return self._semaphores[domain]

    def _build_url(self, url: str, params: Optional[dict] = None) -> str:
        if not params:
            return url

        # Handle list-valued params (e.g., includes[])
        # URL-encode values but keep [] in keys as-is for API compatibility
        parts = []
        for key, value in params.items():
            if isinstance(value, list):
                for v in value:
                    encoded_v = quote(str(v), safe="")
                    parts.append(f"{key}={encoded_v}")
            else:
                encoded_v = quote(str(value), safe="-_.~")
                parts.append(f"{key}={encoded_v}")

        separator = "&" if "?" in url else "?"
        return f"{url}{separator}{'&'.join(parts)}"

    def _make_url(self, url_str: str) -> URL:
        """Create a yarl URL that preserves [] brackets (no re-encoding)."""
        return URL(url_str, encoded=True)

    async def get(
        self,
        url: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
    ) -> Optional[str]:
        """Perform a GET request and return response text."""
        full_url = self._build_url(url, params)
        request_url = self._make_url(full_url)

        try:
            session = await self._get_session()
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            sem = self._get_semaphore(domain)

            async with sem:
                async with session.get(request_url, headers=headers) as response:
                    if response.status == 200:
                        return await response.text()
                    elif response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", "2"))
                        logger.warning(f"Rate limited on {domain}, waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        async with session.get(request_url, headers=headers) as retry_resp:
                            if retry_resp.status == 200:
                                return await retry_resp.text()
                    else:
                        logger.error(f"HTTP {response.status} for {full_url}")
                        return None
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching {full_url}")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching {full_url}: {e}")
            return None

    async def get_json(
        self,
        url: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
    ) -> Optional[dict]:
        """Perform a GET request and return parsed JSON."""
        full_url = self._build_url(url, params)
        request_url = self._make_url(full_url)
        logger.debug(f"GET JSON: {full_url}")

        try:
            session = await self._get_session()
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            sem = self._get_semaphore(domain)

            async with sem:
                async with session.get(request_url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json(content_type=None)
                    elif response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", "2"))
                        logger.warning(f"Rate limited on {domain}, waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        async with session.get(request_url, headers=headers) as retry_resp:
                            if retry_resp.status == 200:
                                return await retry_resp.json(content_type=None)
                    else:
                        logger.error(f"HTTP {response.status} for {full_url}")
                        return None
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching {full_url}")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching {full_url}: {e}")
            return None

    async def get_bytes(
        self,
        url: str,
        headers: Optional[dict] = None,
    ) -> Optional[bytes]:
        """Download binary content (images, files)."""
        request_url = self._make_url(url)
        try:
            session = await self._get_session()
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            sem = self._get_semaphore(domain)

            async with sem:
                async with session.get(request_url, headers=headers) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        logger.error(f"HTTP {response.status} downloading {url}")
                        return None
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            logger.error(f"Error downloading {url}: {e}")
            return None

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
