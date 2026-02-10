"""Generic HTML scraper source - base for creating web-scraping based sources.

This is the equivalent of Tachiyomi's HttpSource/ParsedHttpSource.
Subclass this to create sources that scrape manga websites via HTML parsing.
"""

import logging
from typing import Optional

from bs4 import BeautifulSoup

from models.manga import Manga, Chapter, Page, MangaStatus
from sources.manga_source import MangaSource
from services.network_service import NetworkService

logger = logging.getLogger(__name__)


class ScraperSource(MangaSource):
    """Base class for HTML-scraping manga sources.

    Subclasses must implement the CSS selector methods to parse
    specific manga website layouts.

    Example usage:
        class MyMangaSite(ScraperSource):
            name = "MySite"
            base_url = "https://mysite.com"
            lang = "en"

            # Override selector methods
            def popular_manga_selector(self): return ".manga-card"
            ...
    """

    # === Selectors to override ===

    def popular_manga_url(self, page: int) -> str:
        """URL for the popular manga listing page."""
        return f"{self.base_url}/popular?page={page}"

    def search_manga_url(self, query: str, page: int) -> str:
        """URL for the search results page."""
        return f"{self.base_url}/search?q={query}&page={page}"

    def popular_manga_selector(self) -> str:
        """CSS selector for manga items on the popular page."""
        return ".manga-item"

    def manga_title_selector(self) -> str:
        """CSS selector for manga title within a manga item."""
        return ".title"

    def manga_cover_selector(self) -> str:
        """CSS selector for cover image within a manga item."""
        return "img"

    def manga_url_selector(self) -> str:
        """CSS selector for the link to manga detail page."""
        return "a"

    def chapter_list_selector(self) -> str:
        """CSS selector for chapter list items."""
        return ".chapter-item"

    def chapter_name_selector(self) -> str:
        """CSS selector for chapter name."""
        return ".chapter-title"

    def chapter_url_selector(self) -> str:
        """CSS selector for chapter link."""
        return "a"

    def page_list_selector(self) -> str:
        """CSS selector for page images in the reader."""
        return ".reader-page img"

    # === Implementation ===

    async def _fetch_html(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch a URL and return parsed BeautifulSoup."""
        network = NetworkService.shared()
        html = await network.get(url, headers=self.headers)
        if html:
            return BeautifulSoup(html, "lxml")
        return None

    def _parse_manga_from_element(self, element, source_url: str = "") -> Optional[Manga]:
        """Parse a single manga item from a BeautifulSoup element."""
        try:
            # Title
            title_el = element.select_one(self.manga_title_selector())
            title = title_el.get_text(strip=True) if title_el else ""

            if not title:
                return None

            # URL
            url_el = element.select_one(self.manga_url_selector())
            url = ""
            if url_el:
                href = url_el.get("href", "")
                if href.startswith("/"):
                    url = f"{self.base_url}{href}"
                elif href.startswith("http"):
                    url = href

            # Cover
            cover_el = element.select_one(self.manga_cover_selector())
            cover_url = ""
            if cover_el:
                cover_url = cover_el.get("src", "") or cover_el.get("data-src", "")
                if cover_url.startswith("//"):
                    cover_url = f"https:{cover_url}"
                elif cover_url.startswith("/"):
                    cover_url = f"{self.base_url}{cover_url}"

            # Generate ID from URL
            manga_id = url.split("/")[-1] if url else title.lower().replace(" ", "-")

            return Manga(
                id=manga_id,
                title=title,
                cover_url=cover_url,
                source_id=self.source_id,
                url=url,
            )
        except Exception as e:
            logger.debug(f"Failed to parse manga element: {e}")
            return None

    async def fetch_popular_manga(self, page: int = 1) -> list[Manga]:
        url = self.popular_manga_url(page)
        soup = await self._fetch_html(url)
        if not soup:
            return []

        manga_list = []
        for el in soup.select(self.popular_manga_selector()):
            manga = self._parse_manga_from_element(el)
            if manga:
                manga_list.append(manga)

        return manga_list

    async def search_manga(self, query: str, page: int = 1) -> list[Manga]:
        url = self.search_manga_url(query, page)
        soup = await self._fetch_html(url)
        if not soup:
            return []

        manga_list = []
        for el in soup.select(self.popular_manga_selector()):
            manga = self._parse_manga_from_element(el)
            if manga:
                manga_list.append(manga)

        return manga_list

    async def get_manga_details(self, manga_id: str) -> Manga:
        """Get details - subclasses should override with specific parsing."""
        return Manga(id=manga_id, title=manga_id, source_id=self.source_id)

    async def get_chapter_list(self, manga_id: str) -> list[Chapter]:
        """Get chapters - subclasses should override with specific parsing."""
        return []

    async def get_page_list(self, chapter_id: str) -> list[Page]:
        """Get pages - subclasses should override with specific parsing."""
        return []
