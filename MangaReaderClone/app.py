"""MangaReaderClone - Main application entry point.

A cross-platform manga reader inspired by Tachiyomi with modular extension system.
"""

import asyncio
import logging
import sys
from typing import Optional

from PySide6.QtWidgets import QApplication

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class AppController:
    """Central application controller managing sources, database, and services."""

    def __init__(self):
        self.db = None
        self.repo_parser = None
        self.download_service = None
        self._sources = []

    async def initialize(self):
        """Initialize all services."""
        from services.database_service import DatabaseService
        from services.download_service import DownloadService
        from extensions.repo_parser import RepoParser
        from sources.mangadex_source import MangaDexSource

        # Database
        self.db = DatabaseService()
        await self.db.initialize()

        # Services
        self.repo_parser = RepoParser()
        self.download_service = DownloadService()

        # Register built-in sources
        self._sources = [MangaDexSource()]

        logger.info("Application initialized")

    def get_sources(self):
        """Get all available manga sources."""
        return self._sources

    def get_source_for_manga(self, manga_id: str):
        """Find the source that can handle a specific manga.

        For MangaDex UUIDs, return the MangaDex source.
        Otherwise, try to match by source_id in the database.
        """
        # MangaDex UUIDs are 36 chars with dashes
        if len(manga_id) == 36 and "-" in manga_id:
            for source in self._sources:
                if source.name == "MangaDex":
                    return source

        # Default to first source
        return self._sources[0] if self._sources else None

    async def shutdown(self):
        """Clean up resources."""
        from services.network_service import NetworkService
        await NetworkService.shared().close()
        if self.db:
            await self.db.close()
        logger.info("Application shutdown complete")


def main():
    """Main entry point - starts the Qt application with async support."""
    app = QApplication(sys.argv)
    app.setApplicationName("MangaReaderClone")
    app.setApplicationVersion("1.0.0")

    # Create app controller
    controller = AppController()

    # Try qasync for proper Qt + asyncio integration
    try:
        import qasync

        loop = qasync.QEventLoop(app)
        asyncio.set_event_loop(loop)

        # Initialize services synchronously before showing window
        loop.run_until_complete(controller.initialize())

        from views.main_window import MainWindow
        window = MainWindow(controller)
        window.show()

        # Run the Qt event loop (qasync handles asyncio coroutines)
        # Note: do NOT use `with loop:` because it closes the loop on exit,
        # preventing shutdown cleanup from running.
        try:
            loop.run_forever()
        finally:
            try:
                loop.run_until_complete(controller.shutdown())
            except Exception:
                pass
            loop.close()

    except ImportError:
        logger.warning("qasync not found, using threaded asyncio fallback")
        _run_app_sync(app, controller)


def _run_app_sync(app: QApplication, controller: AppController):
    """Fallback: run async tasks in a background thread."""
    import threading

    async_loop = asyncio.new_event_loop()

    def run_async_loop():
        asyncio.set_event_loop(async_loop)
        async_loop.run_forever()

    async_thread = threading.Thread(target=run_async_loop, daemon=True)
    async_thread.start()

    # Initialize controller in the async thread
    future = asyncio.run_coroutine_threadsafe(controller.initialize(), async_loop)
    future.result(timeout=10)

    # Patch asyncio.ensure_future so UI callbacks dispatch to the async thread
    def patched_ensure_future(coro, *, loop=None):
        if asyncio.iscoroutine(coro):
            return asyncio.run_coroutine_threadsafe(coro, async_loop)
        return asyncio.ensure_future.__wrapped__(coro, loop=loop)

    patched_ensure_future.__wrapped__ = asyncio.ensure_future
    asyncio.ensure_future = patched_ensure_future

    from views.main_window import MainWindow
    window = MainWindow(controller)
    window.show()

    exit_code = app.exec()

    # Cleanup
    future = asyncio.run_coroutine_threadsafe(controller.shutdown(), async_loop)
    try:
        future.result(timeout=5)
    except Exception:
        pass

    async_loop.call_soon_threadsafe(async_loop.stop)
    async_thread.join(timeout=2)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
