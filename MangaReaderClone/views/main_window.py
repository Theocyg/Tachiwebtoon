"""Main application window with tab navigation."""

import asyncio
import logging

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon, QAction, QFont
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QStatusBar, QMenuBar, QToolBar, QLabel,
)

from views.library_view import LibraryView
from views.search_view import SearchView
from views.extensions_view import ExtensionsView
from views.settings_view import SettingsView

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window with Library, Search, Extensions, and Settings tabs."""

    def __init__(self, app_controller):
        super().__init__()
        self.app = app_controller
        self.setWindowTitle("MangaReaderClone")
        self.setMinimumSize(900, 650)
        self.resize(1100, 750)

        self._setup_ui()
        self._setup_menu()

    def _setup_ui(self):
        """Create the tab-based main layout."""
        # Central tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.West)
        self.tabs.setDocumentMode(True)

        font = QFont()
        font.setPointSize(11)
        self.tabs.setFont(font)

        # Create tab views
        self.library_view = LibraryView(self.app)
        self.search_view = SearchView(self.app)
        self.extensions_view = ExtensionsView(self.app)
        self.settings_view = SettingsView(self.app)

        self.tabs.addTab(self.library_view, "Library")
        self.tabs.addTab(self.search_view, "Search")
        self.tabs.addTab(self.extensions_view, "Extensions")
        self.tabs.addTab(self.settings_view, "Settings")

        self.setCentralWidget(self.tabs)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a2e;
            }
            QTabWidget::pane {
                border: none;
                background-color: #16213e;
            }
            QTabBar::tab {
                background-color: #0f3460;
                color: #e0e0e0;
                padding: 12px 8px;
                min-width: 80px;
                border: none;
                border-bottom: 2px solid transparent;
            }
            QTabBar::tab:selected {
                background-color: #533483;
                color: white;
                border-bottom: 2px solid #e94560;
            }
            QTabBar::tab:hover {
                background-color: #1a1a4e;
            }
            QStatusBar {
                background-color: #0f3460;
                color: #a0a0a0;
                font-size: 12px;
            }
            QScrollBar:vertical {
                background: #1a1a2e;
                width: 10px;
            }
            QScrollBar::handle:vertical {
                background: #533483;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

    def _setup_menu(self):
        """Create the menu bar."""
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet("""
            QMenuBar {
                background-color: #0f3460;
                color: #e0e0e0;
            }
            QMenuBar::item:selected {
                background-color: #533483;
            }
            QMenu {
                background-color: #16213e;
                color: #e0e0e0;
                border: 1px solid #533483;
            }
            QMenu::item:selected {
                background-color: #533483;
            }
        """)

        # File menu
        file_menu = menu_bar.addMenu("File")

        refresh_action = QAction("Refresh Library", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._on_refresh)
        file_menu.addAction(refresh_action)

        file_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # View menu
        view_menu = menu_bar.addMenu("View")

        library_action = QAction("Library", self)
        library_action.setShortcut("Ctrl+1")
        library_action.triggered.connect(lambda: self.tabs.setCurrentIndex(0))
        view_menu.addAction(library_action)

        search_action = QAction("Search", self)
        search_action.setShortcut("Ctrl+2")
        search_action.triggered.connect(lambda: self.tabs.setCurrentIndex(1))
        view_menu.addAction(search_action)

        extensions_action = QAction("Extensions", self)
        extensions_action.setShortcut("Ctrl+3")
        extensions_action.triggered.connect(lambda: self.tabs.setCurrentIndex(2))
        view_menu.addAction(extensions_action)

    def _on_refresh(self):
        self.library_view.refresh()
        self.status_bar.showMessage("Library refreshed")

    def show_status(self, message: str, timeout: int = 3000):
        self.status_bar.showMessage(message, timeout)
