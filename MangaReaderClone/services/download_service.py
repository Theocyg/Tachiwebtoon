"""Download service for offline manga chapter storage."""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from models.manga import Chapter, Page
from services.network_service import NetworkService

logger = logging.getLogger(__name__)

DOWNLOAD_DIR = Path.home() / ".mangareaderclone" / "downloads"


class DownloadService:
    """Manages downloading and storing manga chapter pages locally."""

    def __init__(self, download_dir: Optional[Path] = None):
        self._download_dir = download_dir or DOWNLOAD_DIR
        self._download_dir.mkdir(parents=True, exist_ok=True)
        self._active_downloads: dict[str, asyncio.Task] = {}

    def get_chapter_dir(self, manga_id: str, chapter_id: str) -> Path:
        """Get the local directory for a downloaded chapter."""
        safe_manga = manga_id.replace("/", "_")[:50]
        safe_chapter = chapter_id.replace("/", "_")[:50]
        return self._download_dir / safe_manga / safe_chapter

    def is_chapter_downloaded(self, manga_id: str, chapter_id: str) -> bool:
        """Check if a chapter has been downloaded."""
        chapter_dir = self.get_chapter_dir(manga_id, chapter_id)
        return chapter_dir.exists() and any(chapter_dir.iterdir())

    def get_local_pages(self, manga_id: str, chapter_id: str) -> list[Page]:
        """Get locally stored pages for a downloaded chapter."""
        chapter_dir = self.get_chapter_dir(manga_id, chapter_id)
        if not chapter_dir.exists():
            return []

        pages = []
        image_files = sorted(
            [f for f in chapter_dir.iterdir() if f.suffix.lower() in (".jpg", ".png", ".webp", ".gif")],
            key=lambda f: f.name,
        )

        for i, filepath in enumerate(image_files):
            pages.append(Page(
                index=i,
                image_url="",
                chapter_id=chapter_id,
                local_path=str(filepath),
            ))

        return pages

    async def download_chapter(
        self,
        manga_id: str,
        chapter_id: str,
        pages: list[Page],
        headers: Optional[dict] = None,
        progress_callback=None,
    ) -> bool:
        """Download all pages of a chapter to local storage.

        Args:
            manga_id: The manga's unique ID.
            chapter_id: The chapter's unique ID.
            pages: List of pages with image URLs.
            headers: Optional HTTP headers (e.g., Referer).
            progress_callback: Optional callback(current, total) for progress updates.

        Returns:
            True if all pages downloaded successfully.
        """
        chapter_dir = self.get_chapter_dir(manga_id, chapter_id)
        chapter_dir.mkdir(parents=True, exist_ok=True)

        network = NetworkService.shared()
        total = len(pages)
        success_count = 0

        for i, page in enumerate(pages):
            if not page.image_url:
                continue

            # Determine file extension from URL
            ext = ".jpg"
            url_lower = page.image_url.lower()
            for candidate in (".png", ".webp", ".gif"):
                if candidate in url_lower:
                    ext = candidate
                    break

            filepath = chapter_dir / f"{i:04d}{ext}"

            if filepath.exists():
                success_count += 1
                if progress_callback:
                    progress_callback(i + 1, total)
                continue

            data = await network.get_bytes(page.image_url, headers=headers)
            if data:
                filepath.write_bytes(data)
                success_count += 1
                logger.debug(f"Downloaded page {i + 1}/{total} for chapter {chapter_id}")
            else:
                logger.error(f"Failed to download page {i + 1} for chapter {chapter_id}")

            if progress_callback:
                progress_callback(i + 1, total)

            # Small delay to avoid overwhelming the server
            await asyncio.sleep(0.1)

        return success_count == total

    async def delete_chapter(self, manga_id: str, chapter_id: str):
        """Delete downloaded chapter pages."""
        chapter_dir = self.get_chapter_dir(manga_id, chapter_id)
        if chapter_dir.exists():
            import shutil
            shutil.rmtree(chapter_dir)
            logger.info(f"Deleted chapter {chapter_id}")

    def get_download_size(self, manga_id: str, chapter_id: str) -> int:
        """Get total size of downloaded chapter in bytes."""
        chapter_dir = self.get_chapter_dir(manga_id, chapter_id)
        if not chapter_dir.exists():
            return 0
        return sum(f.stat().st_size for f in chapter_dir.rglob("*") if f.is_file())

    def get_total_download_size(self) -> int:
        """Get total size of all downloads in bytes."""
        if not self._download_dir.exists():
            return 0
        return sum(f.stat().st_size for f in self._download_dir.rglob("*") if f.is_file())
