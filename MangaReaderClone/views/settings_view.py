"""Settings view - app configuration."""

import asyncio
import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QCheckBox, QComboBox, QSpinBox, QFrame,
)

from services.download_service import DownloadService

logger = logging.getLogger(__name__)


class SettingsView(QWidget):
    """Application settings."""

    def __init__(self, app_controller, parent=None):
        super().__init__(parent)
        self.app = app_controller
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        title = QLabel("Settings")
        title.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")
        main_layout.addWidget(title)

        # Reader settings
        reader_group = self._create_group("Reader")
        reader_layout = QVBoxLayout(reader_group)

        # Default reading mode
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(self._create_label("Default reading mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Vertical Scroll", "Horizontal (Page)"])
        self.mode_combo.setStyleSheet(self._combo_style())
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        reader_layout.addLayout(mode_layout)

        # Night mode default
        self.night_check = QCheckBox("Enable night mode by default")
        self.night_check.setStyleSheet("QCheckBox { color: #e0e0e0; font-size: 13px; }")
        reader_layout.addWidget(self.night_check)

        main_layout.addWidget(reader_group)

        # Downloads settings
        dl_group = self._create_group("Downloads")
        dl_layout = QVBoxLayout(dl_group)

        # Download path info
        dl_path = DownloadService()._download_dir
        dl_layout.addWidget(self._create_label(f"Download location: {dl_path}"))

        # Storage info
        self.storage_label = self._create_label("Calculating storage usage...")
        dl_layout.addWidget(self.storage_label)

        # Clear downloads
        clear_btn = QPushButton("Clear All Downloads")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #c73652;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
                max-width: 200px;
            }
            QPushButton:hover { background-color: #a02040; }
        """)
        clear_btn.clicked.connect(self._clear_downloads)
        dl_layout.addWidget(clear_btn)

        main_layout.addWidget(dl_group)

        # Network settings
        net_group = self._create_group("Network")
        net_layout = QVBoxLayout(net_group)

        # Concurrent downloads
        conc_layout = QHBoxLayout()
        conc_layout.addWidget(self._create_label("Concurrent page downloads:"))
        self.conc_spin = QSpinBox()
        self.conc_spin.setRange(1, 5)
        self.conc_spin.setValue(3)
        self.conc_spin.setStyleSheet("""
            QSpinBox {
                background-color: #0f3460;
                color: white;
                border: 1px solid #533483;
                border-radius: 4px;
                padding: 4px 8px;
            }
        """)
        conc_layout.addWidget(self.conc_spin)
        conc_layout.addStretch()
        net_layout.addLayout(conc_layout)

        main_layout.addWidget(net_group)

        # About
        about_group = self._create_group("About")
        about_layout = QVBoxLayout(about_group)
        about_layout.addWidget(self._create_label("MangaReaderClone v1.0.0"))
        about_layout.addWidget(self._create_label("A cross-platform manga reader inspired by Tachiyomi"))
        about_layout.addWidget(self._create_label("For educational purposes only"))
        main_layout.addWidget(about_group)

        main_layout.addStretch()

        # Calculate storage
        self._update_storage_info()

    def _create_group(self, title: str) -> QGroupBox:
        group = QGroupBox(title)
        group.setStyleSheet("""
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
        return group

    def _create_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("color: #c0c0c0; font-size: 13px;")
        return label

    def _combo_style(self) -> str:
        return """
            QComboBox {
                background-color: #0f3460;
                color: white;
                border: 1px solid #533483;
                border-radius: 4px;
                padding: 6px 10px;
                min-width: 180px;
            }
            QComboBox QAbstractItemView {
                background-color: #16213e;
                color: white;
                selection-background-color: #533483;
            }
        """

    def _update_storage_info(self):
        dl_service = DownloadService()
        total_bytes = dl_service.get_total_download_size()
        if total_bytes > 1024 * 1024:
            size_str = f"{total_bytes / (1024 * 1024):.1f} MB"
        elif total_bytes > 1024:
            size_str = f"{total_bytes / 1024:.1f} KB"
        else:
            size_str = f"{total_bytes} bytes"
        self.storage_label.setText(f"Storage used: {size_str}")

    def _clear_downloads(self):
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Clear Downloads",
            "Delete all downloaded chapters? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            import shutil
            dl_dir = DownloadService()._download_dir
            if dl_dir.exists():
                shutil.rmtree(dl_dir)
                dl_dir.mkdir(parents=True, exist_ok=True)
            self._update_storage_info()
