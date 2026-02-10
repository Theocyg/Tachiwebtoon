"""Search view - search manga across all active sources."""

import asyncio
import logging

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea,
    QComboBox, QFrame, QProgressBar,
)

from models.manga import Manga
from views.library_view import MangaCard, CARD_WIDTH

logger = logging.getLogger(__name__)


class SearchView(QWidget):
    """Search for manga across installed sources."""

    def __init__(self, app_controller, parent=None):
        super().__init__(parent)
        self.app = app_controller
        self._cards: dict[str, MangaCard] = {}
        self._current_page = 1
        self._current_query = ""
        self._is_loading = False

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Header
        title = QLabel("Search")
        title.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")
        main_layout.addWidget(title)

        # Search bar
        search_layout = QHBoxLayout()

        self.source_combo = QComboBox()
        self.source_combo.setMinimumWidth(150)
        self.source_combo.setStyleSheet("""
            QComboBox {
                background-color: #0f3460;
                color: white;
                border: 1px solid #533483;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #16213e;
                color: white;
                selection-background-color: #533483;
                border: 1px solid #533483;
            }
        """)
        search_layout.addWidget(self.source_combo)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search manga by title...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #0f3460;
                color: white;
                border: 1px solid #533483;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #e94560;
            }
        """)
        self.search_input.returnPressed.connect(self._on_search)
        search_layout.addWidget(self.search_input, stretch=1)

        search_btn = QPushButton("Search")
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #e94560;
                color: white;
                border: none;
                padding: 8px 24px;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c73652;
            }
            QPushButton:disabled {
                background-color: #555;
            }
        """)
        search_btn.clicked.connect(self._on_search)
        self.search_btn = search_btn
        search_layout.addWidget(search_btn)

        main_layout.addLayout(search_layout)

        # Popular manga button
        popular_layout = QHBoxLayout()
        popular_btn = QPushButton("Browse Popular")
        popular_btn.setStyleSheet("""
            QPushButton {
                background-color: #533483;
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e94560;
            }
        """)
        popular_btn.clicked.connect(self._on_browse_popular)
        popular_layout.addWidget(popular_btn)
        popular_layout.addStretch()

        self.result_count_label = QLabel("")
        self.result_count_label.setStyleSheet("color: #888; font-size: 12px;")
        popular_layout.addWidget(self.result_count_label)

        main_layout.addLayout(popular_layout)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setMaximum(0)  # Indeterminate
        self.progress.setFixedHeight(3)
        self.progress.setVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: none;
                background: transparent;
            }
            QProgressBar::chunk {
                background-color: #e94560;
            }
        """)
        main_layout.addWidget(self.progress)

        # Results grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.scroll_area.setWidget(self.grid_container)
        main_layout.addWidget(self.scroll_area)

        # Load more button
        self.load_more_btn = QPushButton("Load More")
        self.load_more_btn.setVisible(False)
        self.load_more_btn.setStyleSheet("""
            QPushButton {
                background-color: #533483;
                color: white;
                border: none;
                padding: 10px 32px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e94560;
            }
        """)
        self.load_more_btn.clicked.connect(self._on_load_more)
        main_layout.addWidget(self.load_more_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Empty state
        self.empty_label = QLabel("Enter a search term or browse popular manga")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #666; font-size: 14px; padding: 40px;")
        main_layout.addWidget(self.empty_label)

        # Populate sources dropdown
        QTimer.singleShot(200, self._populate_sources)

    def _populate_sources(self):
        """Populate the source dropdown."""
        self.source_combo.clear()
        for source in self.app.get_sources():
            self.source_combo.addItem(source.name, source.source_id)

    def _on_search(self):
        query = self.search_input.text().strip()
        if not query or self._is_loading:
            return
        self._current_query = query
        self._current_page = 1
        self._clear_results()
        asyncio.ensure_future(self._do_search(query, 1))

    def _on_browse_popular(self):
        if self._is_loading:
            return
        self._current_query = ""
        self._current_page = 1
        self._clear_results()
        asyncio.ensure_future(self._do_popular(1))

    def _on_load_more(self):
        if self._is_loading:
            return
        self._current_page += 1
        if self._current_query:
            asyncio.ensure_future(self._do_search(self._current_query, self._current_page))
        else:
            asyncio.ensure_future(self._do_popular(self._current_page))

    def _clear_results(self):
        for card in self._cards.values():
            card.deleteLater()
        self._cards.clear()
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _set_loading(self, loading: bool):
        self._is_loading = loading
        self.progress.setVisible(loading)
        self.search_btn.setEnabled(not loading)

    async def _do_search(self, query: str, page: int):
        self._set_loading(True)
        self.empty_label.setVisible(False)

        source = self._get_selected_source()
        if not source:
            self._set_loading(False)
            self.empty_label.setText("No source selected. Install extensions first.")
            self.empty_label.setVisible(True)
            return

        try:
            results = await source.search_manga(query, page)
            self._display_results(results, append=(page > 1))
            self.result_count_label.setText(f"{len(self._cards)} results")
            self.load_more_btn.setVisible(len(results) >= 20)

            # Load covers
            for manga in results:
                if manga.cover_url and manga.id in self._cards:
                    asyncio.ensure_future(self._load_cover(manga))

        except Exception as e:
            logger.error(f"Search failed: {e}")
            self.empty_label.setText(f"Search failed: {e}")
            self.empty_label.setVisible(True)
        finally:
            self._set_loading(False)

    async def _do_popular(self, page: int):
        self._set_loading(True)
        self.empty_label.setVisible(False)

        source = self._get_selected_source()
        if not source:
            self._set_loading(False)
            self.empty_label.setText("No source selected. Install extensions first.")
            self.empty_label.setVisible(True)
            return

        try:
            results = await source.fetch_popular_manga(page)
            self._display_results(results, append=(page > 1))
            self.result_count_label.setText(f"{len(self._cards)} results (Popular)")
            self.load_more_btn.setVisible(len(results) >= 20)

            for manga in results:
                if manga.cover_url and manga.id in self._cards:
                    asyncio.ensure_future(self._load_cover(manga))

        except Exception as e:
            logger.error(f"Browse popular failed: {e}")
            self.empty_label.setText(f"Failed to load: {e}")
            self.empty_label.setVisible(True)
        finally:
            self._set_loading(False)

    def _get_selected_source(self):
        idx = self.source_combo.currentIndex()
        sources = self.app.get_sources()
        if idx >= 0 and idx < len(sources):
            return sources[idx]
        return None

    def _display_results(self, manga_list: list[Manga], append: bool = False):
        if not append:
            self._clear_results()

        available_width = self.scroll_area.viewport().width() or 800
        cols = max(2, available_width // (CARD_WIDTH + 12))
        start_idx = len(self._cards)

        for i, manga in enumerate(manga_list):
            if manga.id in self._cards:
                continue

            card = MangaCard(manga)
            card.clicked.connect(self._on_manga_clicked)
            card.set_cover_placeholder()

            idx = start_idx + i
            row = idx // cols
            col = idx % cols
            self.grid_layout.addWidget(card, row, col)
            self._cards[manga.id] = card

        self.empty_label.setVisible(len(self._cards) == 0)
        self.scroll_area.setVisible(len(self._cards) > 0)

    async def _load_cover(self, manga: Manga):
        try:
            from services.network_service import NetworkService
            network = NetworkService.shared()
            data = await network.get_bytes(manga.cover_url)
            if data and manga.id in self._cards:
                image = QImage()
                image.loadFromData(data)
                if not image.isNull():
                    pixmap = QPixmap.fromImage(image)
                    self._cards[manga.id].set_cover_image(pixmap)
        except Exception as e:
            logger.debug(f"Failed to load cover: {e}")

    def _on_manga_clicked(self, manga_id: str):
        asyncio.ensure_future(self._open_manga_detail(manga_id))

    async def _open_manga_detail(self, manga_id: str):
        from views.manga_detail_view import MangaDetailDialog

        # First ensure we have the manga stored
        source = self._get_selected_source()
        if source:
            try:
                manga = await source.get_manga_details(manga_id)
                manga.source_id = source.source_id
                await self.app.db.upsert_manga(manga)
            except Exception as e:
                logger.error(f"Failed to get manga details: {e}")

        dialog = MangaDetailDialog(manga_id, self.app, self)
        dialog.exec()
