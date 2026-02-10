"""Extensions view - browse and manage extension repos."""

import asyncio
import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QGroupBox,
    QFrame, QMessageBox, QProgressBar,
)

from models.manga import ExtensionInfo

logger = logging.getLogger(__name__)


class ExtensionsView(QWidget):
    """Manage extension repositories and browse available extensions."""

    def __init__(self, app_controller, parent=None):
        super().__init__(parent)
        self.app = app_controller
        self._setup_ui()

        # Load repos on init
        from PySide6.QtCore import QTimer
        QTimer.singleShot(300, lambda: asyncio.ensure_future(self._load_repos()))

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # Header
        title = QLabel("Extensions")
        title.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")
        main_layout.addWidget(title)

        # Add repo section
        repo_group = QGroupBox("Extension Repositories")
        repo_group.setStyleSheet("""
            QGroupBox {
                color: #e0e0e0;
                border: 1px solid #533483;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 16px;
                font-size: 14px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                padding: 0 8px;
            }
        """)
        repo_layout = QVBoxLayout(repo_group)

        # URL input
        url_layout = QHBoxLayout()
        self.repo_url_input = QLineEdit()
        self.repo_url_input.setPlaceholderText("Enter repo URL (e.g., https://raw.githubusercontent.com/.../index.min.json)")
        self.repo_url_input.setStyleSheet("""
            QLineEdit {
                background-color: #0f3460;
                color: white;
                border: 1px solid #533483;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #e94560;
            }
        """)
        self.repo_url_input.returnPressed.connect(lambda: asyncio.ensure_future(self._add_repo()))
        url_layout.addWidget(self.repo_url_input, stretch=1)

        add_btn = QPushButton("Add Repo")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #e94560;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c73652;
            }
        """)
        add_btn.clicked.connect(lambda: asyncio.ensure_future(self._add_repo()))
        url_layout.addWidget(add_btn)

        repo_layout.addLayout(url_layout)

        # Repo list
        self.repo_list = QListWidget()
        self.repo_list.setMaximumHeight(120)
        self.repo_list.setStyleSheet("""
            QListWidget {
                background-color: #16213e;
                color: #e0e0e0;
                border: 1px solid #0f3460;
                border-radius: 4px;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 6px 8px;
            }
            QListWidget::item:selected {
                background-color: #533483;
            }
        """)
        repo_layout.addWidget(self.repo_list)

        # Repo actions
        repo_actions = QHBoxLayout()
        refresh_btn = QPushButton("Refresh All")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #533483;
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #e94560; }
        """)
        refresh_btn.clicked.connect(lambda: asyncio.ensure_future(self._refresh_repos()))
        repo_actions.addWidget(refresh_btn)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #c73652;
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #a02040; }
        """)
        remove_btn.clicked.connect(lambda: asyncio.ensure_future(self._remove_repo()))
        repo_actions.addWidget(remove_btn)

        repo_actions.addStretch()
        repo_layout.addLayout(repo_actions)

        main_layout.addWidget(repo_group)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setMaximum(0)
        self.progress.setFixedHeight(3)
        self.progress.setVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar { border: none; background: transparent; }
            QProgressBar::chunk { background-color: #e94560; }
        """)
        main_layout.addWidget(self.progress)

        # Available extensions list
        ext_header = QHBoxLayout()
        ext_label = QLabel("Available Extensions")
        ext_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        ext_header.addWidget(ext_label)

        self.ext_count_label = QLabel("")
        self.ext_count_label.setStyleSheet("color: #888; font-size: 12px;")
        ext_header.addWidget(self.ext_count_label)
        ext_header.addStretch()

        # Filter
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter extensions...")
        self.filter_input.setMaximumWidth(250)
        self.filter_input.setStyleSheet("""
            QLineEdit {
                background-color: #0f3460;
                color: white;
                border: 1px solid #533483;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 12px;
            }
        """)
        self.filter_input.textChanged.connect(self._filter_extensions)
        ext_header.addWidget(self.filter_input)

        main_layout.addLayout(ext_header)

        self.ext_list = QListWidget()
        self.ext_list.setStyleSheet("""
            QListWidget {
                background-color: #16213e;
                color: #e0e0e0;
                border: 1px solid #0f3460;
                border-radius: 4px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #0f3460;
            }
            QListWidget::item:hover {
                background-color: #1a1a4e;
            }
            QListWidget::item:selected {
                background-color: #533483;
            }
        """)
        main_layout.addWidget(self.ext_list)

        self._all_extensions: list[ExtensionInfo] = []

    async def _load_repos(self):
        """Load saved repos from database."""
        try:
            repos = await self.app.db.get_repos()
            self.repo_list.clear()
            for repo in repos:
                item = QListWidgetItem(f"{repo['name'] or 'Unnamed'} - {repo['url']}")
                item.setData(Qt.ItemDataRole.UserRole, repo["url"])
                self.repo_list.addItem(item)

            # Auto-refresh extensions
            if repos:
                await self._refresh_repos()
        except Exception as e:
            logger.error(f"Failed to load repos: {e}")

    async def _add_repo(self):
        """Add a new extension repository."""
        url = self.repo_url_input.text().strip()
        if not url:
            return

        if not url.startswith("http"):
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid HTTP/HTTPS URL")
            return

        self.progress.setVisible(True)

        try:
            repo = await self.app.repo_parser.fetch_repo(url)
            if repo:
                await self.app.db.add_repo(url, repo.name)
                self.repo_url_input.clear()
                await self._load_repos()
                logger.info(f"Added repo: {url} ({len(repo.extensions)} extensions)")
            else:
                QMessageBox.warning(self, "Failed", "Could not fetch or parse the repository.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add repo: {e}")
        finally:
            self.progress.setVisible(False)

    async def _remove_repo(self):
        """Remove the selected repo."""
        item = self.repo_list.currentItem()
        if not item:
            return

        url = item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self, "Remove Repository",
            f"Remove this repository?\n{url}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            await self.app.db.remove_repo(url)
            await self._load_repos()

    async def _refresh_repos(self):
        """Refresh all repos and update extension list."""
        self.progress.setVisible(True)
        self._all_extensions.clear()

        try:
            repos = await self.app.db.get_repos()
            for repo_data in repos:
                url = repo_data["url"]
                repo = await self.app.repo_parser.fetch_repo(url)
                if repo:
                    self._all_extensions.extend(repo.extensions)

            self._display_extensions(self._all_extensions)
            self.ext_count_label.setText(f"({len(self._all_extensions)} total)")
        except Exception as e:
            logger.error(f"Failed to refresh repos: {e}")
        finally:
            self.progress.setVisible(False)

    def _display_extensions(self, extensions: list[ExtensionInfo]):
        self.ext_list.clear()
        for ext in sorted(extensions, key=lambda e: e.name):
            nsfw_tag = " [NSFW]" if ext.nsfw else ""
            text = f"{ext.name} ({ext.lang}) v{ext.version}{nsfw_tag}  |  {ext.pkg}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, ext)
            self.ext_list.addItem(item)

    def _filter_extensions(self, text: str):
        if not text:
            self._display_extensions(self._all_extensions)
            return

        filtered = [
            ext for ext in self._all_extensions
            if text.lower() in ext.name.lower() or text.lower() in ext.pkg.lower()
        ]
        self._display_extensions(filtered)
