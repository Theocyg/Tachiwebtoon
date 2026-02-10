"""Data models for the manga reader application."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class MangaStatus(Enum):
    UNKNOWN = 0
    ONGOING = 1
    COMPLETED = 2
    LICENSED = 3
    PUBLISHING_FINISHED = 4
    CANCELLED = 5
    ON_HIATUS = 6


@dataclass
class Manga:
    id: str
    title: str
    cover_url: str = ""
    description: str = ""
    author: str = ""
    artist: str = ""
    status: MangaStatus = MangaStatus.UNKNOWN
    genres: list[str] = field(default_factory=list)
    source_id: str = ""
    url: str = ""
    in_library: bool = False
    last_updated: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "cover_url": self.cover_url,
            "description": self.description,
            "author": self.author,
            "artist": self.artist,
            "status": self.status.value,
            "genres": ",".join(self.genres),
            "source_id": self.source_id,
            "url": self.url,
            "in_library": self.in_library,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Manga":
        return cls(
            id=data["id"],
            title=data["title"],
            cover_url=data.get("cover_url", ""),
            description=data.get("description", ""),
            author=data.get("author", ""),
            artist=data.get("artist", ""),
            status=MangaStatus(data.get("status", 0)),
            genres=data.get("genres", "").split(",") if data.get("genres") else [],
            source_id=data.get("source_id", ""),
            url=data.get("url", ""),
            in_library=bool(data.get("in_library", False)),
            last_updated=datetime.fromisoformat(data["last_updated"]) if data.get("last_updated") else None,
        )


@dataclass
class Chapter:
    id: str
    manga_id: str
    name: str
    url: str
    chapter_number: float = 0.0
    date_upload: Optional[datetime] = None
    scanlator: str = ""
    language: str = "en"
    downloaded: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "manga_id": self.manga_id,
            "name": self.name,
            "url": self.url,
            "chapter_number": self.chapter_number,
            "date_upload": self.date_upload.isoformat() if self.date_upload else None,
            "scanlator": self.scanlator,
            "language": self.language,
            "downloaded": self.downloaded,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Chapter":
        return cls(
            id=data["id"],
            manga_id=data["manga_id"],
            name=data["name"],
            url=data["url"],
            chapter_number=float(data.get("chapter_number", 0)),
            date_upload=datetime.fromisoformat(data["date_upload"]) if data.get("date_upload") else None,
            scanlator=data.get("scanlator", ""),
            language=data.get("language", "en"),
            downloaded=bool(data.get("downloaded", False)),
        )


@dataclass
class Page:
    index: int
    image_url: str
    chapter_id: str = ""
    local_path: str = ""

    @property
    def is_downloaded(self) -> bool:
        return bool(self.local_path)


@dataclass
class ExtensionInfo:
    pkg: str
    name: str
    apk: str
    lang: str
    code: int
    version: str
    nsfw: int = 0
    sources: list[dict] = field(default_factory=list)
    icon_url: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "ExtensionInfo":
        return cls(
            pkg=data.get("pkg", ""),
            name=data.get("name", ""),
            apk=data.get("apk", ""),
            lang=data.get("lang", "en"),
            code=data.get("code", 0),
            version=data.get("version", "1.0"),
            nsfw=data.get("nsfw", 0),
            sources=data.get("sources", []),
            icon_url=data.get("icon", ""),
        )


@dataclass
class ExtensionRepo:
    url: str
    name: str = ""
    extensions: list[ExtensionInfo] = field(default_factory=list)
