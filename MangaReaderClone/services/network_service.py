"""Network service for HTTP requests with caching and rate limiting."""

import asyncio
import logging
from typing import Optional
from urllib.parse import urlencode, urljoin

import aiohttp

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
        parts = []
        for key, value in params.items():
            if isinstance(value, list):
                for v in value:
                    parts.append(f"{key}={v}")
            else:
                parts.append(f"{key}={value}")

        separator = "&" if "?" in url else "?"
        return f"{url}{separator}{'&'.join(parts)}"

    async def get(
        self,
        url: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
    ) -> Optional[str]:
        """Perform a GET request and return response text."""
        full_url = self._build_url(url, params)

        try:
            session = await self._get_session()
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            sem = self._get_semaphore(domain)

            async with sem:
                async with session.get(full_url, headers=headers) as response:
                    if response.status == 200:
                        return await response.text()
                    elif response.status == 429:
                        # Rate limited, wait and retry once
                        retry_after = int(response.headers.get("Retry-After", "2"))
                        logger.warning(f"Rate limited on {domain}, waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        async with session.get(full_url, headers=headers) as retry_resp:
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

        try:
            session = await self._get_session()
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            sem = self._get_semaphore(domain)

            async with sem:
                async with session.get(full_url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json(content_type=None)
                    elif response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", "2"))
                        logger.warning(f"Rate limited on {domain}, waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        async with session.get(full_url, headers=headers) as retry_resp:
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
        try:
            session = await self._get_session()
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            sem = self._get_semaphore(domain)

            async with sem:
                async with session.get(url, headers=headers) as response:
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
