"""Library view - shows manga in the user's collection."""

import asyncio
import logging
from typing import Optional

from PySide6.QtCore import Qt, QSize, Signal, QTimer
from PySide6.QtGui import QPixmap, QImage, QFont, QCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QScrollArea, QPushButton, QFrame, QMenu,
    QMessageBox, QSizePolicy,
)

from models.manga import Manga

logger = logging.getLogger(__name__)

CARD_WIDTH = 160
CARD_HEIGHT = 260
COVER_HEIGHT = 200


class MangaCard(QFrame):
    """A clickable manga cover card for the library grid."""

    clicked = Signal(str)  # manga_id
    right_clicked = Signal(str, object)  # manga_id, QPoint

    def __init__(self, manga: Manga, parent=None):
        super().__init__(parent)
        self.manga = manga
        self.setFixedSize(CARD_WIDTH, CARD_HEIGHT)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet("""
            MangaCard {
                background-color: #16213e;
                border-radius: 8px;
                border: 1px solid #0f3460;
            }
            MangaCard:hover {
                border: 1px solid #e94560;
                background-color: #1a1a4e;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Cover image
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(CARD_WIDTH - 8, COVER_HEIGHT)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet("""
            QLabel {
                background-color: #0f3460;
                border-radius: 6px;
                color: #666;
                font-size: 10px;
            }
        """)
        self.cover_label.setText("Loading...")
        layout.addWidget(self.cover_label)

        # Title
        title_label = QLabel(manga.title)
        title_label.setWordWrap(True)
        title_label.setMaximumHeight(50)
        title_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        title_label.setStyleSheet("""
            QLabel {
                color: #e0e0e0;
                font-size: 11px;
                font-weight: bold;
                padding: 2px;
            }
        """)
        layout.addWidget(title_label)

    def set_cover_image(self, pixmap: QPixmap):
        """Set the cover image from a QPixmap."""
        scaled = pixmap.scaled(
            CARD_WIDTH - 8, COVER_HEIGHT,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        # Crop to fit
        if scaled.width() > CARD_WIDTH - 8 or scaled.height() > COVER_HEIGHT:
            x = (scaled.width() - (CARD_WIDTH - 8)) // 2
            y = (scaled.height() - COVER_HEIGHT) // 2
            scaled = scaled.copy(max(0, x), max(0, y), CARD_WIDTH - 8, COVER_HEIGHT)
        self.cover_label.setPixmap(scaled)

    def set_cover_placeholder(self):
        self.cover_label.setText(self.manga.title[:20])

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.manga.id)
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit(self.manga.id, event.globalPosition().toPoint())
        super().mousePressEvent(event)


class LibraryView(QWidget):
    """Grid view showing all manga in the user's library."""

    manga_selected = Signal(str)  # manga_id

    def __init__(self, app_controller, parent=None):
        super().__init__(parent)
        self.app = app_controller
        self._cards: dict[str, MangaCard] = {}

        self._setup_ui()

        # Load library on next event loop
        QTimer.singleShot(100, self.refresh)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Header
        header = QHBoxLayout()
        title = QLabel("Library")
        title.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")
        header.addWidget(title)

        header.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #533483;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e94560;
            }
        """)
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)

        main_layout.addLayout(header)

        # Scrollable grid area
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

        # Empty state
        self.empty_label = QLabel("Your library is empty.\nSearch for manga and add them to your library.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #666; font-size: 16px; padding: 40px;")
        main_layout.addWidget(self.empty_label)

    def refresh(self):
        """Reload library from database."""
        asyncio.ensure_future(self._load_library())

    async def _load_library(self):
        """Load manga library from the database."""
        try:
            library = await self.app.db.get_library()
            self._display_manga_list(library)

            # Load covers asynchronously
            for manga in library:
                if manga.cover_url and manga.id in self._cards:
                    asyncio.ensure_future(self._load_cover(manga))
        except Exception as e:
            logger.error(f"Failed to load library: {e}")

    def _display_manga_list(self, manga_list: list[Manga]):
        """Display manga in a grid layout."""
        # Clear existing cards
        for card in self._cards.values():
            card.deleteLater()
        self._cards.clear()

        # Clear grid layout
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Show/hide empty state
        self.empty_label.setVisible(len(manga_list) == 0)
        self.scroll_area.setVisible(len(manga_list) > 0)

        if not manga_list:
            return

        # Calculate columns based on available width
        available_width = self.scroll_area.viewport().width() or 800
        cols = max(2, available_width // (CARD_WIDTH + 12))

        for i, manga in enumerate(manga_list):
            card = MangaCard(manga)
            card.clicked.connect(self._on_manga_clicked)
            card.right_clicked.connect(self._on_manga_right_click)
            card.set_cover_placeholder()

            row = i // cols
            col = i % cols
            self.grid_layout.addWidget(card, row, col)
            self._cards[manga.id] = card

    async def _load_cover(self, manga: Manga):
        """Load a manga cover image from URL."""
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
            logger.debug(f"Failed to load cover for {manga.title}: {e}")

    def _on_manga_clicked(self, manga_id: str):
        """Open manga detail/chapter list view."""
        self.manga_selected.emit(manga_id)
        # Open detail window
        asyncio.ensure_future(self._open_manga_detail(manga_id))

    async def _open_manga_detail(self, manga_id: str):
        """Open the manga detail dialog."""
        from views.manga_detail_view import MangaDetailDialog
        dialog = MangaDetailDialog(manga_id, self.app, self)
        dialog.exec()
        # Refresh library in case changes were made
        self.refresh()

    def _on_manga_right_click(self, manga_id: str, pos):
        """Show context menu for a manga card."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #16213e;
                color: #e0e0e0;
                border: 1px solid #533483;
            }
            QMenu::item:selected {
                background-color: #533483;
            }
        """)

        remove_action = menu.addAction("Remove from Library")
        remove_action.triggered.connect(lambda: asyncio.ensure_future(self._remove_from_library(manga_id)))

        menu.exec(pos)

    async def _remove_from_library(self, manga_id: str):
        """Remove a manga from the library."""
        reply = QMessageBox.question(
            self, "Remove from Library",
            "Remove this manga from your library?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            await self.app.db.remove_from_library(manga_id)
            self.refresh()
