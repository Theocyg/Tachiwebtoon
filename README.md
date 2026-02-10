# MangaReaderClone

A cross-platform manga reader inspired by Tachiyomi/Tachimanga with a modular extension system for scraping manga sources.

## Features

- **Modular Extension System**: Add manga sources via JSON repository URLs (compatible with Tachiyomi-style repos)
- **Library Management**: Track and organize your manga collection locally
- **Search**: Search manga across all installed sources
- **Reader**: Horizontal/vertical scroll modes with zoom and night mode
- **Offline Reading**: Download chapters for offline access
- **No Backend**: Everything runs client-side with web scraping

## Project Structure

```
MangaReaderClone/          # Python Desktop App (cross-platform)
├── models/                # Data models (Manga, Chapter, Page)
├── sources/               # MangaSource implementations
├── views/                 # UI components (Library, Search, Reader)
├── services/              # Network, Database, Download services
├── extensions/            # Extension/repo parser system
├── app.py                 # Main entry point
└── requirements.txt       # Python dependencies

ios/                       # iOS App (Swift/SwiftUI)
└── MangaReaderClone/      # Xcode project source files
```

## Desktop App (Python)

### Requirements

- Python 3.9+
- pip

### Installation

```bash
cd MangaReaderClone
pip install -r requirements.txt
python app.py
```

### Dependencies

- **PySide6**: Qt-based cross-platform GUI
- **beautifulsoup4 + lxml**: HTML parsing/scraping (equivalent to SwiftSoup)
- **aiohttp**: Async HTTP client (equivalent to Alamofire)
- **Pillow**: Image processing
- **aiosqlite**: Async SQLite for local storage (equivalent to Core Data)

## iOS App (Swift)

### Requirements

- Xcode 14+
- iOS 15+
- Swift Package Manager dependencies:
  - Alamofire
  - SwiftSoup
  - Kingfisher

### Build

1. Open `ios/MangaReaderClone.xcodeproj` in Xcode
2. Wait for SPM to resolve dependencies
3. Build and run on simulator or device

## Adding Extensions

1. Go to Settings > Extension Repos
2. Add a repo URL (e.g., `https://raw.githubusercontent.com/keiyoushi/extensions/repo/index.min.json`)
3. Browse available extensions and install them
4. Sources will appear in the Search tab

## Architecture

### MangaSource Protocol

All manga sources implement the `MangaSource` interface:

```python
class MangaSource(ABC):
    name: str
    base_url: str
    lang: str

    async def fetch_popular_manga(page: int) -> List[Manga]
    async def search_manga(query: str, page: int) -> List[Manga]
    async def get_manga_details(manga_id: str) -> Manga
    async def get_chapter_list(manga_id: str) -> List[Chapter]
    async def get_page_list(chapter_id: str) -> List[Page]
```

### Built-in Sources

- **MangaDex**: Uses the official MangaDex API v5
- Custom sources can be added by implementing the MangaSource protocol

## License

This project is for educational purposes only. Respect copyright laws and the terms of service of manga hosting sites.
