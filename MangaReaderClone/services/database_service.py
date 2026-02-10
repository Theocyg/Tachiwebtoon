"""SQLite database service for local manga library storage."""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

import aiosqlite

from models.manga import Manga, Chapter, MangaStatus

logger = logging.getLogger(__name__)

DB_DIR = Path.home() / ".mangareaderclone"
DB_PATH = DB_DIR / "library.db"


class DatabaseService:
    """Async SQLite database for library, chapters, and download tracking."""

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or DB_PATH
        self._db: Optional[aiosqlite.Connection] = None

    async def initialize(self):
        """Create the database and tables if they don't exist."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        self._db = await aiosqlite.connect(str(self._db_path))
        self._db.row_factory = aiosqlite.Row

        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS manga (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                cover_url TEXT DEFAULT '',
                description TEXT DEFAULT '',
                author TEXT DEFAULT '',
                artist TEXT DEFAULT '',
                status INTEGER DEFAULT 0,
                genres TEXT DEFAULT '',
                source_id TEXT DEFAULT '',
                url TEXT DEFAULT '',
                in_library INTEGER DEFAULT 0,
                last_updated TEXT
            );

            CREATE TABLE IF NOT EXISTS chapter (
                id TEXT PRIMARY KEY,
                manga_id TEXT NOT NULL,
                name TEXT NOT NULL,
                url TEXT DEFAULT '',
                chapter_number REAL DEFAULT 0,
                date_upload TEXT,
                scanlator TEXT DEFAULT '',
                language TEXT DEFAULT 'en',
                downloaded INTEGER DEFAULT 0,
                read INTEGER DEFAULT 0,
                last_page_read INTEGER DEFAULT 0,
                FOREIGN KEY (manga_id) REFERENCES manga(id)
            );

            CREATE TABLE IF NOT EXISTS extension_repo (
                url TEXT PRIMARY KEY,
                name TEXT DEFAULT '',
                last_fetched TEXT
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_chapter_manga ON chapter(manga_id);
            CREATE INDEX IF NOT EXISTS idx_manga_library ON manga(in_library);
        """)
        await self._db.commit()
        logger.info(f"Database initialized at {self._db_path}")

    async def close(self):
        if self._db:
            await self._db.close()

    # === Manga operations ===

    async def get_library(self) -> list[Manga]:
        """Get all manga in the user's library."""
        async with self._db.execute(
            "SELECT * FROM manga WHERE in_library = 1 ORDER BY title"
        ) as cursor:
            rows = await cursor.fetchall()
            return [Manga.from_dict(dict(row)) for row in rows]

    async def upsert_manga(self, manga: Manga):
        """Insert or update a manga entry."""
        data = manga.to_dict()
        await self._db.execute("""
            INSERT INTO manga (id, title, cover_url, description, author, artist,
                             status, genres, source_id, url, in_library, last_updated)
            VALUES (:id, :title, :cover_url, :description, :author, :artist,
                    :status, :genres, :source_id, :url, :in_library, :last_updated)
            ON CONFLICT(id) DO UPDATE SET
                title = :title,
                cover_url = :cover_url,
                description = :description,
                author = :author,
                artist = :artist,
                status = :status,
                genres = :genres,
                url = :url,
                last_updated = :last_updated
        """, data)
        await self._db.commit()

    async def add_to_library(self, manga_id: str):
        """Add a manga to the library."""
        await self._db.execute(
            "UPDATE manga SET in_library = 1 WHERE id = ?", (manga_id,)
        )
        await self._db.commit()

    async def remove_from_library(self, manga_id: str):
        """Remove a manga from the library."""
        await self._db.execute(
            "UPDATE manga SET in_library = 0 WHERE id = ?", (manga_id,)
        )
        await self._db.commit()

    async def is_in_library(self, manga_id: str) -> bool:
        async with self._db.execute(
            "SELECT in_library FROM manga WHERE id = ?", (manga_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return bool(row and row["in_library"])

    async def get_manga(self, manga_id: str) -> Optional[Manga]:
        async with self._db.execute(
            "SELECT * FROM manga WHERE id = ?", (manga_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return Manga.from_dict(dict(row)) if row else None

    # === Chapter operations ===

    async def upsert_chapters(self, chapters: list[Chapter]):
        """Insert or update multiple chapters."""
        for ch in chapters:
            data = ch.to_dict()
            await self._db.execute("""
                INSERT INTO chapter (id, manga_id, name, url, chapter_number,
                                   date_upload, scanlator, language, downloaded)
                VALUES (:id, :manga_id, :name, :url, :chapter_number,
                        :date_upload, :scanlator, :language, :downloaded)
                ON CONFLICT(id) DO UPDATE SET
                    name = :name,
                    url = :url,
                    chapter_number = :chapter_number,
                    date_upload = :date_upload,
                    scanlator = :scanlator
            """, data)
        await self._db.commit()

    async def get_chapters(self, manga_id: str) -> list[Chapter]:
        """Get all chapters for a manga, sorted by chapter number descending."""
        async with self._db.execute(
            "SELECT * FROM chapter WHERE manga_id = ? ORDER BY chapter_number DESC",
            (manga_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [Chapter.from_dict(dict(row)) for row in rows]

    async def mark_chapter_downloaded(self, chapter_id: str, downloaded: bool = True):
        await self._db.execute(
            "UPDATE chapter SET downloaded = ? WHERE id = ?",
            (int(downloaded), chapter_id),
        )
        await self._db.commit()

    async def mark_chapter_read(self, chapter_id: str, last_page: int = 0):
        await self._db.execute(
            "UPDATE chapter SET read = 1, last_page_read = ? WHERE id = ?",
            (last_page, chapter_id),
        )
        await self._db.commit()

    # === Extension repo operations ===

    async def get_repos(self) -> list[dict]:
        async with self._db.execute("SELECT * FROM extension_repo") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def add_repo(self, url: str, name: str = ""):
        await self._db.execute(
            "INSERT OR REPLACE INTO extension_repo (url, name) VALUES (?, ?)",
            (url, name),
        )
        await self._db.commit()

    async def remove_repo(self, url: str):
        await self._db.execute("DELETE FROM extension_repo WHERE url = ?", (url,))
        await self._db.commit()

    # === Settings ===

    async def get_setting(self, key: str, default: str = "") -> str:
        async with self._db.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ) as cursor:
            row = await cursor.fetchone()
            return row["value"] if row else default

    async def set_setting(self, key: str, value: str):
        await self._db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        await self._db.commit()
