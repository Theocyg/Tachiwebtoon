"""MangaDex source implementation using the official API v5."""

import logging
from datetime import datetime
from typing import Optional

from models.manga import Manga, Chapter, Page, MangaStatus
from sources.manga_source import MangaSource
from services.network_service import NetworkService

logger = logging.getLogger(__name__)

# MangaDex API base
API_BASE = "https://api.mangadex.org"

STATUS_MAP = {
    "ongoing": MangaStatus.ONGOING,
    "completed": MangaStatus.COMPLETED,
    "hiatus": MangaStatus.ON_HIATUS,
    "cancelled": MangaStatus.CANCELLED,
}


class MangaDexSource(MangaSource):
    """MangaDex source using the public API v5 (no scraping needed)."""

    @property
    def name(self) -> str:
        return "MangaDex"

    @property
    def base_url(self) -> str:
        return "https://mangadex.org"

    @property
    def lang(self) -> str:
        return "en"

    @property
    def headers(self) -> dict[str, str]:
        return {
            "User-Agent": "MangaReaderClone/1.0",
        }

    def _parse_manga(self, data: dict) -> Manga:
        """Parse a MangaDex API manga object into our Manga model."""
        attrs = data.get("attributes", {})
        relationships = data.get("relationships", [])

        # Get title (prefer English)
        titles = attrs.get("title", {})
        title = titles.get("en") or titles.get("ja-ro") or next(iter(titles.values()), "Unknown")

        # Get description
        descriptions = attrs.get("description", {})
        description = descriptions.get("en", "") or next(iter(descriptions.values()), "")

        # Get cover art filename
        cover_url = ""
        for rel in relationships:
            if rel.get("type") == "cover_art":
                cover_filename = rel.get("attributes", {}).get("fileName", "")
                if cover_filename:
                    cover_url = f"https://uploads.mangadex.org/covers/{data['id']}/{cover_filename}.256.jpg"
                break

        # Get author/artist
        author = ""
        artist = ""
        for rel in relationships:
            if rel.get("type") == "author" and not author:
                author = rel.get("attributes", {}).get("name", "")
            elif rel.get("type") == "artist" and not artist:
                artist = rel.get("attributes", {}).get("name", "")

        # Status
        status = STATUS_MAP.get(attrs.get("status", ""), MangaStatus.UNKNOWN)

        # Genres/tags
        genres = []
        for tag in attrs.get("tags", []):
            tag_name = tag.get("attributes", {}).get("name", {}).get("en", "")
            if tag_name:
                genres.append(tag_name)

        return Manga(
            id=data["id"],
            title=title,
            cover_url=cover_url,
            description=description,
            author=author,
            artist=artist or author,
            status=status,
            genres=genres,
            source_id=self.source_id,
            url=f"{self.base_url}/title/{data['id']}",
        )

    async def fetch_popular_manga(self, page: int = 1) -> list[Manga]:
        """Fetch popular manga from MangaDex."""
        limit = 20
        offset = (page - 1) * limit

        params = {
            "limit": str(limit),
            "offset": str(offset),
            "order[followedCount]": "desc",
            "includes[]": ["cover_art", "author", "artist"],
            "availableTranslatedLanguage[]": ["en"],
            "hasAvailableChapters": "true",
            "contentRating[]": ["safe", "suggestive"],
        }

        network = NetworkService.shared()
        data = await network.get_json(f"{API_BASE}/manga", params=params, headers=self.headers)

        if not data or "data" not in data:
            logger.error("Failed to fetch popular manga from MangaDex")
            return []

        return [self._parse_manga(item) for item in data["data"]]

    async def search_manga(self, query: str, page: int = 1) -> list[Manga]:
        """Search manga on MangaDex by title."""
        limit = 20
        offset = (page - 1) * limit

        params = {
            "title": query,
            "limit": str(limit),
            "offset": str(offset),
            "order[relevance]": "desc",
            "includes[]": ["cover_art", "author", "artist"],
            "availableTranslatedLanguage[]": ["en"],
            "contentRating[]": ["safe", "suggestive"],
        }

        network = NetworkService.shared()
        data = await network.get_json(f"{API_BASE}/manga", params=params, headers=self.headers)

        if not data or "data" not in data:
            logger.error(f"Failed to search manga on MangaDex: {query}")
            return []

        return [self._parse_manga(item) for item in data["data"]]

    async def get_manga_details(self, manga_id: str) -> Manga:
        """Get detailed info about a specific manga."""
        params = {
            "includes[]": ["cover_art", "author", "artist"],
        }

        network = NetworkService.shared()
        data = await network.get_json(f"{API_BASE}/manga/{manga_id}", params=params, headers=self.headers)

        if not data or "data" not in data:
            raise ValueError(f"Manga not found: {manga_id}")

        return self._parse_manga(data["data"])

    async def get_chapter_list(self, manga_id: str) -> list[Chapter]:
        """Get chapters for a manga (prefers English, falls back to all languages)."""
        # Try English first
        chapters = await self._fetch_chapters(manga_id, lang="en")
        if chapters:
            return chapters

        # Fallback: fetch all languages if no English chapters found
        logger.info(f"No English chapters for {manga_id}, fetching all languages")
        return await self._fetch_chapters(manga_id, lang=None)

    async def _fetch_chapters(self, manga_id: str, lang: str | None = "en") -> list[Chapter]:
        """Fetch chapters, optionally filtered by language."""
        chapters = []
        offset = 0
        limit = 100

        network = NetworkService.shared()

        while True:
            params = {
                "manga": manga_id,
                "limit": str(limit),
                "offset": str(offset),
                "order[chapter]": "desc",
                "includes[]": ["scanlation_group"],
                "contentRating[]": ["safe", "suggestive", "erotica"],
            }
            if lang:
                params["translatedLanguage[]"] = [lang]

            data = await network.get_json(f"{API_BASE}/chapter", params=params, headers=self.headers)

            if not data or "data" not in data:
                break

            for item in data["data"]:
                attrs = item.get("attributes", {})

                # Chapter number
                ch_num = attrs.get("chapter")
                try:
                    chapter_number = float(ch_num) if ch_num else 0.0
                except (ValueError, TypeError):
                    chapter_number = 0.0

                # Chapter name
                ch_title = attrs.get("title", "")
                name = f"Chapter {ch_num or '?'}"
                if ch_title:
                    name += f" - {ch_title}"

                # Scanlator
                scanlator = ""
                for rel in item.get("relationships", []):
                    if rel.get("type") == "scanlation_group":
                        scanlator = rel.get("attributes", {}).get("name", "")
                        break

                # Date
                date_str = attrs.get("publishAt", "")
                date_upload = None
                if date_str:
                    try:
                        date_upload = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    except ValueError:
                        pass

                chapters.append(Chapter(
                    id=item["id"],
                    manga_id=manga_id,
                    name=name,
                    url=f"{self.base_url}/chapter/{item['id']}",
                    chapter_number=chapter_number,
                    date_upload=date_upload,
                    scanlator=scanlator,
                    language="en",
                ))

            total = data.get("total", 0)
            offset += limit
            if offset >= total:
                break

        return chapters

    async def get_page_list(self, chapter_id: str) -> list[Page]:
        """Get page image URLs for a chapter via MangaDex@Home."""
        network = NetworkService.shared()
        data = await network.get_json(
            f"{API_BASE}/at-home/server/{chapter_id}",
            headers=self.headers,
        )

        if not data:
            raise ValueError(f"Failed to get pages for chapter: {chapter_id}")

        base_server = data.get("baseUrl", "")
        chapter_hash = data.get("chapter", {}).get("hash", "")
        page_filenames = data.get("chapter", {}).get("data", [])

        pages = []
        for i, filename in enumerate(page_filenames):
            image_url = f"{base_server}/data/{chapter_hash}/{filename}"
            pages.append(Page(
                index=i,
                image_url=image_url,
                chapter_id=chapter_id,
            ))

        return pages
