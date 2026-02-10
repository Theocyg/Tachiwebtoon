"""Abstract base class for all manga sources."""

from abc import ABC, abstractmethod
from models.manga import Manga, Chapter, Page


class MangaSource(ABC):
    """Protocol/interface that all manga sources must implement.

    Equivalent to the Tachiyomi HttpSource interface.
    Each source represents a manga website or API that can be scraped.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Display name of the source."""
        ...

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Base URL of the manga source website."""
        ...

    @property
    @abstractmethod
    def lang(self) -> str:
        """Language code (e.g., 'en', 'fr', 'ja')."""
        ...

    @property
    def source_id(self) -> str:
        """Unique identifier for this source."""
        return f"{self.lang}/{self.name.lower().replace(' ', '_')}"

    @property
    def headers(self) -> dict[str, str]:
        """Default HTTP headers for requests to this source."""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.base_url,
        }

    @abstractmethod
    async def fetch_popular_manga(self, page: int = 1) -> list[Manga]:
        """Fetch a page of popular/trending manga.

        Args:
            page: Page number (1-indexed).

        Returns:
            List of Manga objects.
        """
        ...

    @abstractmethod
    async def search_manga(self, query: str, page: int = 1) -> list[Manga]:
        """Search for manga by title.

        Args:
            query: Search query string.
            page: Page number (1-indexed).

        Returns:
            List of matching Manga objects.
        """
        ...

    @abstractmethod
    async def get_manga_details(self, manga_id: str) -> Manga:
        """Get detailed information about a specific manga.

        Args:
            manga_id: Unique identifier for the manga on this source.

        Returns:
            Manga object with full details.
        """
        ...

    @abstractmethod
    async def get_chapter_list(self, manga_id: str) -> list[Chapter]:
        """Get the list of chapters for a manga.

        Args:
            manga_id: Unique identifier for the manga.

        Returns:
            List of Chapter objects, sorted by chapter number descending.
        """
        ...

    @abstractmethod
    async def get_page_list(self, chapter_id: str) -> list[Page]:
        """Get the list of pages/images for a chapter.

        Args:
            chapter_id: Unique identifier for the chapter.

        Returns:
            List of Page objects with image URLs.
        """
        ...
