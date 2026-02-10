"""Extension repository parser - fetches and parses Tachiyomi-compatible repo JSON."""

import json
import logging
from typing import Optional

from models.manga import ExtensionInfo, ExtensionRepo
from services.network_service import NetworkService

logger = logging.getLogger(__name__)


class RepoParser:
    """Parses Tachiyomi-compatible extension repository index files.

    Repo format (index.min.json):
    [
        {
            "pkg": "eu.kanade.tachiyomi.extension.en.mangadex",
            "apk": "tachiyomi-en-mangadex-v1.4.289.apk",
            "name": "MangaDex",
            "lang": "en",
            "code": 289,
            "version": "1.4.289",
            "nsfw": 0,
            "sources": [{"name": "MangaDex", "lang": "en", "id": 2499283573021220255}],
            "icon": "https://raw.githubusercontent.com/.../icon.png"
        },
        ...
    ]
    """

    def __init__(self):
        self._repos: dict[str, ExtensionRepo] = {}

    async def fetch_repo(self, url: str) -> Optional[ExtensionRepo]:
        """Fetch and parse a repository index from URL.

        Args:
            url: URL to the repo index JSON file.

        Returns:
            ExtensionRepo with parsed extension list, or None on error.
        """
        network = NetworkService.shared()
        logger.info(f"Fetching repo index: {url}")

        data = await network.get_json(url)
        if data is None:
            logger.error(f"Failed to fetch repo: {url}")
            return None

        return self.parse_repo(url, data)

    def parse_repo(self, url: str, data) -> ExtensionRepo:
        """Parse repo JSON data into ExtensionRepo.

        Args:
            url: The repo URL (used as identifier).
            data: Parsed JSON data (list of extension entries).

        Returns:
            ExtensionRepo with extensions list.
        """
        extensions = []

        # The data can be a list (index.min.json) or a dict with a key
        ext_list = data if isinstance(data, list) else data.get("extensions", data.get("data", []))

        for item in ext_list:
            if not isinstance(item, dict):
                continue

            try:
                ext = ExtensionInfo.from_dict(item)
                # Build icon URL relative to repo if not absolute
                if ext.icon_url and not ext.icon_url.startswith("http"):
                    base_url = url.rsplit("/", 1)[0]
                    ext.icon_url = f"{base_url}/{ext.icon_url}"
                extensions.append(ext)
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to parse extension entry: {e}")
                continue

        # Derive repo name from URL
        repo_name = url.split("//")[-1].split("/")[1] if "//" in url else url

        repo = ExtensionRepo(url=url, name=repo_name, extensions=extensions)
        self._repos[url] = repo

        logger.info(f"Parsed {len(extensions)} extensions from {repo_name}")
        return repo

    def get_extensions_by_lang(self, lang: str) -> list[ExtensionInfo]:
        """Get all extensions for a specific language across all repos."""
        results = []
        for repo in self._repos.values():
            for ext in repo.extensions:
                if ext.lang == lang:
                    results.append(ext)
        return results

    def get_all_extensions(self) -> list[ExtensionInfo]:
        """Get all extensions from all loaded repos."""
        results = []
        for repo in self._repos.values():
            results.extend(repo.extensions)
        return results

    def search_extensions(self, query: str) -> list[ExtensionInfo]:
        """Search extensions by name across all repos."""
        query_lower = query.lower()
        results = []
        for repo in self._repos.values():
            for ext in repo.extensions:
                if query_lower in ext.name.lower() or query_lower in ext.pkg.lower():
                    results.append(ext)
        return results
