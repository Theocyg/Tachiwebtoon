"""Manga detail view - shows manga info and chapter list."""

import asyncio
import logging

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QScrollArea, QWidget,
    QSplitter, QFrame, QMessageBox,
)

from models.manga import Manga, Chapter

logger = logging.getLogger(__name__)

BTN_STYLE = """
    QPushButton {{
        background-color: {bg};
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        font-size: 12px;
    }}
    QPushButton:hover {{
        background-color: {hover};
    }}
"""


class MangaDetailDialog(QDialog):
    """Dialog showing manga details and chapter list."""

    def __init__(self, manga_id: str, app_controller, parent=None):
        super().__init__(parent)
        self.manga_id = manga_id
        self.app = app_controller
        self.manga: Manga | None = None
        self.chapters: list[Chapter] = []

        self.setWindowTitle("Manga Details")
        self.setMinimumSize(700, 500)
        self.resize(850, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a2e;
            }
        """)

        self._setup_ui()
        self._data_loaded = False

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # --- Top section: Manga info ---
        info_frame = QFrame()
        info_frame.setStyleSheet("QFrame { background-color: #16213e; }")
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(16, 16, 16, 16)

        # Cover
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(180, 260)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet("""
            QLabel {
                background-color: #0f3460;
                border-radius: 8px;
                color: #666;
            }
        """)
        self.cover_label.setText("Loading...")
        info_layout.addWidget(self.cover_label)

        # Details
        details_layout = QVBoxLayout()
        details_layout.setSpacing(8)

        self.title_label = QLabel("Loading...")
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
        details_layout.addWidget(self.title_label)

        self.author_label = QLabel("")
        self.author_label.setStyleSheet("color: #a0a0a0; font-size: 13px;")
        details_layout.addWidget(self.author_label)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #e94560; font-size: 12px;")
        details_layout.addWidget(self.status_label)

        self.genres_label = QLabel("")
        self.genres_label.setWordWrap(True)
        self.genres_label.setStyleSheet("color: #888; font-size: 11px;")
        details_layout.addWidget(self.genres_label)

        # Description (scrollable)
        desc_scroll = QScrollArea()
        desc_scroll.setWidgetResizable(True)
        desc_scroll.setMaximumHeight(120)
        desc_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.desc_label = QLabel("")
        self.desc_label.setWordWrap(True)
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.desc_label.setStyleSheet("color: #c0c0c0; font-size: 12px; padding: 4px;")
        desc_scroll.setWidget(self.desc_label)
        details_layout.addWidget(desc_scroll)

        # Buttons
        btn_layout = QHBoxLayout()

        self.library_btn = QPushButton("Add to Library")
        self.library_btn.setStyleSheet(BTN_STYLE.format(bg="#533483", hover="#e94560"))
        self.library_btn.clicked.connect(lambda: asyncio.ensure_future(self._toggle_library()))
        btn_layout.addWidget(self.library_btn)

        btn_layout.addStretch()
        details_layout.addLayout(btn_layout)

        info_layout.addLayout(details_layout, stretch=1)
        splitter.addWidget(info_frame)

        # --- Bottom section: Chapter list ---
        chapter_frame = QFrame()
        chapter_frame.setStyleSheet("QFrame { background-color: #1a1a2e; }")
        chapter_layout = QVBoxLayout(chapter_frame)
        chapter_layout.setContentsMargins(16, 8, 16, 8)

        ch_header = QHBoxLayout()
        self.chapter_count_label = QLabel("Chapters")
        self.chapter_count_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        ch_header.addWidget(self.chapter_count_label)
        ch_header.addStretch()
        chapter_layout.addLayout(ch_header)

        self.chapter_list = QListWidget()
        self.chapter_list.setStyleSheet("""
            QListWidget {
                background-color: #16213e;
                color: #e0e0e0;
                border: 1px solid #0f3460;
                border-radius: 4px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 10px 12px;
                border-bottom: 1px solid #0f3460;
            }
            QListWidget::item:hover {
                background-color: #1a1a4e;
            }
            QListWidget::item:selected {
                background-color: #533483;
            }
        """)
        self.chapter_list.itemDoubleClicked.connect(self._on_chapter_double_click)
        chapter_layout.addWidget(self.chapter_list)

        splitter.addWidget(chapter_frame)
        splitter.setSizes([300, 300])

        layout.addWidget(splitter)

    def showEvent(self, event):
        """Trigger async data loading once the dialog is visible."""
        super().showEvent(event)
        if not self._data_loaded:
            self._data_loaded = True
            asyncio.ensure_future(self._load_data())

    async def _load_data(self):
        """Load manga details and chapter list."""
        logger.info(f"Loading data for manga_id={self.manga_id}")
        try:
            # Try DB first
            self.manga = await self.app.db.get_manga(self.manga_id)
            if self.manga:
                self._update_manga_info()

            # Get source for this manga
            source = self.app.get_source_for_manga(self.manga_id)
            if not source:
                logger.warning(f"No source found for manga {self.manga_id}")
                self.chapters = await self.app.db.get_chapters(self.manga_id)
                self._update_chapter_list()
                return

            logger.info(f"Using source: {source.name}")

            # Refresh details from source
            try:
                manga = await source.get_manga_details(self.manga_id)
                manga.source_id = source.source_id
                # Preserve library status
                if self.manga:
                    manga.in_library = self.manga.in_library
                self.manga = manga
                await self.app.db.upsert_manga(manga)
                self._update_manga_info()
            except Exception as e:
                logger.warning(f"Could not refresh manga details: {e}")

            # Load chapters
            try:
                logger.info(f"Fetching chapters for {self.manga_id}...")
                self.chapters = await source.get_chapter_list(self.manga_id)
                logger.info(f"Got {len(self.chapters)} chapters")
                await self.app.db.upsert_chapters(self.chapters)
                self._update_chapter_list()
            except Exception as e:
                logger.error(f"Failed to load chapters: {e}", exc_info=True)
                # Try from DB
                self.chapters = await self.app.db.get_chapters(self.manga_id)
                self._update_chapter_list()

            # Load cover
            if self.manga and self.manga.cover_url:
                await self._load_cover()

        except Exception as e:
            logger.error(f"Failed to load manga detail: {e}", exc_info=True)

    def _update_manga_info(self):
        if not self.manga:
            return

        self.title_label.setText(self.manga.title)
        self.setWindowTitle(self.manga.title)

        parts = []
        if self.manga.author:
            parts.append(f"Author: {self.manga.author}")
        if self.manga.artist and self.manga.artist != self.manga.author:
            parts.append(f"Artist: {self.manga.artist}")
        self.author_label.setText(" | ".join(parts))

        self.status_label.setText(self.manga.status.name.replace("_", " ").title())
        self.genres_label.setText(", ".join(self.manga.genres) if self.manga.genres else "")
        self.desc_label.setText(self.manga.description)

        # Update library button
        if self.manga.in_library:
            self.library_btn.setText("In Library")
            self.library_btn.setStyleSheet(BTN_STYLE.format(bg="#e94560", hover="#c73652"))
        else:
            self.library_btn.setText("Add to Library")
            self.library_btn.setStyleSheet(BTN_STYLE.format(bg="#533483", hover="#e94560"))

    def _update_chapter_list(self):
        self.chapter_list.clear()
        self.chapter_count_label.setText(f"Chapters ({len(self.chapters)})")

        for ch in self.chapters:
            date_str = ch.date_upload.strftime("%Y-%m-%d") if ch.date_upload else ""
            text = ch.name
            if ch.scanlator:
                text += f"  [{ch.scanlator}]"
            if date_str:
                text += f"  ({date_str})"

            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, ch.id)
            self.chapter_list.addItem(item)

    async def _load_cover(self):
        try:
            from services.network_service import NetworkService
            network = NetworkService.shared()
            data = await network.get_bytes(self.manga.cover_url)
            if data:
                image = QImage()
                image.loadFromData(data)
                if not image.isNull():
                    pixmap = QPixmap.fromImage(image).scaled(
                        180, 260,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    self.cover_label.setPixmap(pixmap)
        except Exception as e:
            logger.debug(f"Failed to load cover: {e}")

    async def _toggle_library(self):
        if not self.manga:
            return

        if self.manga.in_library:
            await self.app.db.remove_from_library(self.manga.id)
            self.manga.in_library = False
        else:
            await self.app.db.upsert_manga(self.manga)
            await self.app.db.add_to_library(self.manga.id)
            self.manga.in_library = True

        self._update_manga_info()

    def _on_chapter_double_click(self, item: QListWidgetItem):
        chapter_id = item.data(Qt.ItemDataRole.UserRole)
        if chapter_id:
            self._open_reader_sync(chapter_id)

    def _open_reader_sync(self, chapter_id: str):
        """Open the chapter reader (non-blocking)."""
        from views.reader_view import ReaderDialog

        # Find the chapter
        chapter = None
        for ch in self.chapters:
            if ch.id == chapter_id:
                chapter = ch
                break

        if not chapter:
            return

        # Get page list
        source = self.app.get_source_for_manga(self.manga_id)
        if not source:
            QMessageBox.warning(self, "Error", "Source not available")
            return

        # Create and show reader (it loads pages async internally)
        dialog = ReaderDialog(
            manga_title=self.manga.title if self.manga else "",
            chapter=chapter,
            pages=[],  # will be loaded async inside the reader
            chapters=self.chapters,
            app_controller=self.app,
            parent=self,
        )
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.show()

        # Kick off page loading after the dialog is shown
        async def _load_and_set_pages():
            try:
                pages = await source.get_page_list(chapter_id)
                if pages:
                    dialog.pages = pages
                    await dialog._load_all_pages()
                else:
                    dialog.close()
                    QMessageBox.warning(self, "Error", "No pages found for this chapter")
            except Exception as e:
                logger.error(f"Failed to load pages: {e}")
                dialog.close()

        asyncio.ensure_future(_load_and_set_pages())
