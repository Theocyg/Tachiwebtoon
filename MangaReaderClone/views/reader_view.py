"""Manga chapter reader - horizontal/vertical scroll with zoom and night mode."""

import asyncio
import logging

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import (
    QPixmap, QImage, QKeySequence, QShortcut, QColor,
    QPainter, QWheelEvent,
)
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QToolBar, QSlider, QFrame, QComboBox,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QSizePolicy, QApplication,
)

from models.manga import Chapter, Page

logger = logging.getLogger(__name__)

TOOLBAR_STYLE = """
    QToolBar {
        background-color: #0f3460;
        border: none;
        padding: 4px;
        spacing: 8px;
    }
    QPushButton {
        background-color: #533483;
        color: white;
        border: none;
        padding: 6px 12px;
        border-radius: 4px;
        font-size: 12px;
    }
    QPushButton:hover {
        background-color: #e94560;
    }
    QPushButton:disabled {
        background-color: #333;
        color: #666;
    }
    QLabel {
        color: white;
        font-size: 12px;
    }
    QComboBox {
        background-color: #0f3460;
        color: white;
        border: 1px solid #533483;
        border-radius: 4px;
        padding: 4px 8px;
    }
"""


class PageWidget(QLabel):
    """Widget that displays a single manga page image."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumHeight(200)
        self._original_pixmap: QPixmap | None = None
        self._night_mode = False

    def set_image(self, pixmap: QPixmap):
        self._original_pixmap = pixmap
        self._apply_and_display()

    def set_night_mode(self, enabled: bool):
        self._night_mode = enabled
        self._apply_and_display()

    def _apply_and_display(self):
        if not self._original_pixmap:
            return

        pixmap = self._original_pixmap

        if self._night_mode:
            image = pixmap.toImage()
            image.invertPixels(QImage.InvertMode.InvertRgb)
            pixmap = QPixmap.fromImage(image)

        # Scale to fit width
        available_width = self.parentWidget().width() - 20 if self.parentWidget() else 800
        if pixmap.width() > available_width:
            pixmap = pixmap.scaledToWidth(
                available_width,
                Qt.TransformationMode.SmoothTransformation,
            )

        self.setPixmap(pixmap)
        self.setFixedHeight(pixmap.height())


class ReaderDialog(QDialog):
    """Full-screen manga chapter reader."""

    def __init__(
        self,
        manga_title: str,
        chapter: Chapter,
        pages: list[Page],
        chapters: list[Chapter],
        app_controller,
        parent=None,
    ):
        super().__init__(parent)
        self.manga_title = manga_title
        self.chapter = chapter
        self.pages = pages
        self.chapters = chapters
        self.app = app_controller
        self._page_widgets: list[PageWidget] = []
        self._current_page = 0
        self._night_mode = False
        self._is_vertical = True

        self.setWindowTitle(f"{manga_title} - {chapter.name}")
        self.setMinimumSize(800, 600)
        self.showMaximized()
        self.setStyleSheet("QDialog { background-color: #111; }")

        self._setup_ui()
        self._setup_shortcuts()

        # Start loading pages
        asyncio.ensure_future(self._load_all_pages())

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        toolbar = QFrame()
        toolbar.setStyleSheet(TOOLBAR_STYLE)
        toolbar.setFixedHeight(44)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 4, 8, 4)

        # Chapter navigation
        self.prev_ch_btn = QPushButton("<< Prev Ch.")
        self.prev_ch_btn.clicked.connect(lambda: asyncio.ensure_future(self._prev_chapter()))
        toolbar_layout.addWidget(self.prev_ch_btn)

        # Chapter info
        self.chapter_label = QLabel(self.chapter.name)
        self.chapter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toolbar_layout.addWidget(self.chapter_label, stretch=1)

        self.next_ch_btn = QPushButton("Next Ch. >>")
        self.next_ch_btn.clicked.connect(lambda: asyncio.ensure_future(self._next_chapter()))
        toolbar_layout.addWidget(self.next_ch_btn)

        toolbar_layout.addWidget(QLabel("  |  "))

        # Page indicator
        self.page_label = QLabel("0/0")
        toolbar_layout.addWidget(self.page_label)

        toolbar_layout.addWidget(QLabel("  |  "))

        # Mode toggle
        mode_btn = QPushButton("Vertical/Horizontal")
        mode_btn.clicked.connect(self._toggle_mode)
        toolbar_layout.addWidget(mode_btn)

        # Night mode
        night_btn = QPushButton("Night Mode")
        night_btn.clicked.connect(self._toggle_night)
        toolbar_layout.addWidget(night_btn)

        # Close
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        toolbar_layout.addWidget(close_btn)

        layout.addWidget(toolbar)

        # --- Vertical scroll reader ---
        self.vertical_reader = QScrollArea()
        self.vertical_reader.setWidgetResizable(True)
        self.vertical_reader.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.vertical_reader.setStyleSheet("""
            QScrollArea { border: none; background-color: #111; }
        """)

        self.pages_container = QWidget()
        self.pages_container.setStyleSheet("background-color: #111;")
        self.pages_layout = QVBoxLayout(self.pages_container)
        self.pages_layout.setContentsMargins(0, 0, 0, 0)
        self.pages_layout.setSpacing(4)
        self.pages_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        self.vertical_reader.setWidget(self.pages_container)
        self.vertical_reader.verticalScrollBar().valueChanged.connect(self._on_scroll)

        layout.addWidget(self.vertical_reader)

        # --- Horizontal page reader (hidden by default) ---
        self.horizontal_reader = QWidget()
        self.horizontal_reader.setStyleSheet("background-color: #111;")
        h_layout = QVBoxLayout(self.horizontal_reader)
        h_layout.setContentsMargins(0, 0, 0, 0)

        self.single_page = PageWidget()
        self.single_page.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_layout.addWidget(self.single_page, stretch=1)

        # Page nav buttons
        nav_layout = QHBoxLayout()
        self.h_prev_btn = QPushButton("<< Previous Page")
        self.h_prev_btn.setStyleSheet(TOOLBAR_STYLE)
        self.h_prev_btn.clicked.connect(self._prev_page)
        nav_layout.addWidget(self.h_prev_btn)
        nav_layout.addStretch()
        self.h_next_btn = QPushButton("Next Page >>")
        self.h_next_btn.setStyleSheet(TOOLBAR_STYLE)
        self.h_next_btn.clicked.connect(self._next_page)
        nav_layout.addWidget(self.h_next_btn)
        h_layout.addLayout(nav_layout)

        self.horizontal_reader.setVisible(False)
        layout.addWidget(self.horizontal_reader)

        # Update chapter nav buttons
        self._update_chapter_nav()

    def _setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, self._next_page)
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, self._prev_page)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.close)
        QShortcut(QKeySequence(Qt.Key.Key_N), self, self._toggle_night)
        QShortcut(QKeySequence(Qt.Key.Key_V), self, self._toggle_mode)

    async def _load_all_pages(self):
        """Load all page images (lazy - loads visible first)."""
        from services.network_service import NetworkService
        network = NetworkService.shared()

        total = len(self.pages)
        self.page_label.setText(f"Loading... 0/{total}")

        # Create placeholder widgets
        for i, page in enumerate(self.pages):
            pw = PageWidget(self.pages_container)
            pw.setText(f"Loading page {i + 1}...")
            pw.setStyleSheet("color: #666; font-size: 14px; min-height: 300px;")
            self.pages_layout.addWidget(pw)
            self._page_widgets.append(pw)

        # Load pages sequentially (respects server rate limits)
        for i, page in enumerate(self.pages):
            try:
                data = await network.get_bytes(page.image_url)
                if data and i < len(self._page_widgets):
                    image = QImage()
                    image.loadFromData(data)
                    if not image.isNull():
                        pixmap = QPixmap.fromImage(image)
                        self._page_widgets[i].set_image(pixmap)
                        self._page_widgets[i].set_night_mode(self._night_mode)
                    else:
                        self._page_widgets[i].setText(f"Failed to decode page {i + 1}")
                else:
                    if i < len(self._page_widgets):
                        self._page_widgets[i].setText(f"Failed to load page {i + 1}")
            except Exception as e:
                logger.error(f"Error loading page {i + 1}: {e}")
                if i < len(self._page_widgets):
                    self._page_widgets[i].setText(f"Error: {e}")

            self.page_label.setText(f"{i + 1}/{total}")
            # Let UI update
            QApplication.processEvents()

        self.page_label.setText(f"1/{total}")
        self._current_page = 0

        # Show first page in horizontal mode
        if self._page_widgets and self._page_widgets[0]._original_pixmap:
            self.single_page.set_image(self._page_widgets[0]._original_pixmap)
            self.single_page.set_night_mode(self._night_mode)

    def _on_scroll(self, value):
        """Track current page based on scroll position in vertical mode."""
        if not self._is_vertical or not self._page_widgets:
            return

        viewport_top = value
        for i, pw in enumerate(self._page_widgets):
            widget_top = pw.y()
            widget_bottom = widget_top + pw.height()
            if widget_top <= viewport_top + 100 <= widget_bottom:
                self._current_page = i
                self.page_label.setText(f"{i + 1}/{len(self.pages)}")
                break

    def _next_page(self):
        if self._current_page < len(self.pages) - 1:
            self._current_page += 1
            self._go_to_page(self._current_page)

    def _prev_page(self):
        if self._current_page > 0:
            self._current_page -= 1
            self._go_to_page(self._current_page)

    def _go_to_page(self, index: int):
        self.page_label.setText(f"{index + 1}/{len(self.pages)}")

        if self._is_vertical:
            # Scroll to page widget
            if index < len(self._page_widgets):
                self.vertical_reader.ensureWidgetVisible(self._page_widgets[index])
        else:
            # Show single page
            if index < len(self._page_widgets) and self._page_widgets[index]._original_pixmap:
                self.single_page.set_image(self._page_widgets[index]._original_pixmap)
                self.single_page.set_night_mode(self._night_mode)

    def _toggle_mode(self):
        self._is_vertical = not self._is_vertical
        self.vertical_reader.setVisible(self._is_vertical)
        self.horizontal_reader.setVisible(not self._is_vertical)

        if not self._is_vertical:
            self._go_to_page(self._current_page)

    def _toggle_night(self):
        self._night_mode = not self._night_mode
        for pw in self._page_widgets:
            pw.set_night_mode(self._night_mode)
        if not self._is_vertical:
            self._go_to_page(self._current_page)

        bg = "#eee" if self._night_mode else "#111"
        self.pages_container.setStyleSheet(f"background-color: {bg};")
        self.horizontal_reader.setStyleSheet(f"background-color: {bg};")

    def _update_chapter_nav(self):
        """Enable/disable prev/next chapter buttons."""
        current_idx = -1
        for i, ch in enumerate(self.chapters):
            if ch.id == self.chapter.id:
                current_idx = i
                break

        # Chapters are sorted descending, so "next" = lower index, "prev" = higher index
        self.next_ch_btn.setEnabled(current_idx > 0)
        self.prev_ch_btn.setEnabled(current_idx < len(self.chapters) - 1)

    async def _next_chapter(self):
        current_idx = -1
        for i, ch in enumerate(self.chapters):
            if ch.id == self.chapter.id:
                current_idx = i
                break

        if current_idx > 0:
            await self._switch_chapter(self.chapters[current_idx - 1])

    async def _prev_chapter(self):
        current_idx = -1
        for i, ch in enumerate(self.chapters):
            if ch.id == self.chapter.id:
                current_idx = i
                break

        if current_idx < len(self.chapters) - 1:
            await self._switch_chapter(self.chapters[current_idx + 1])

    async def _switch_chapter(self, new_chapter: Chapter):
        """Switch to a different chapter."""
        source = self.app.get_source_for_manga(self.chapter.manga_id)
        if not source:
            return

        try:
            new_pages = await source.get_page_list(new_chapter.id)
            if not new_pages:
                return

            # Clear current pages
            for pw in self._page_widgets:
                pw.deleteLater()
            self._page_widgets.clear()

            self.chapter = new_chapter
            self.pages = new_pages
            self._current_page = 0
            self.chapter_label.setText(new_chapter.name)
            self.setWindowTitle(f"{self.manga_title} - {new_chapter.name}")
            self._update_chapter_nav()

            await self._load_all_pages()
        except Exception as e:
            logger.error(f"Failed to switch chapter: {e}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self._next_page()
        else:
            super().keyPressEvent(event)
