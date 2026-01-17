# -*- coding: utf-8 -*-
"""
RenForge TM (Translation Memory) Page

MVP Implementation (v2):
- Read-only list of TM entries
- Local search/filter functionality
- Import TMX button (disabled with tooltip)
- Sample data to show functionality
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QHeaderView, QTableWidgetItem

from qfluentwidgets import (
    SubtitleLabel, BodyLabel, PushButton, SearchLineEdit, 
    TableWidget, FluentIcon as FIF, CardWidget, InfoBar, InfoBarPosition
)

from renforge_logger import get_logger

logger = get_logger("gui.pages.tm")


# Sample TM entries for demonstration
SAMPLE_TM_ENTRIES = [
    ("Hello there!", "Merhaba!", "100", "gemini"),
    ("How are you?", "Nasılsın?", "100", "google"),
    ("I love you", "Seni seviyorum", "100", "user"),
    ("Good morning", "Günaydın", "100", "google"),
    ("Good night", "İyi geceler", "100", "gemini"),
    ("Thank you", "Teşekkür ederim", "100", "user"),
    ("You're welcome", "Rica ederim", "100", "gemini"),
    ("What's your name?", "Adın ne?", "100", "google"),
    ("My name is [player]", "Benim adım [player]", "100", "user"),
    ("See you later", "Görüşürüz", "100", "gemini"),
    ("I don't understand", "Anlamıyorum", "100", "google"),
    ("Can you help me?", "Bana yardım edebilir misin?", "100", "user"),
    ("Where is the library?", "Kütüphane nerede?", "85", "fuzzy"),
    ("I'm looking for...", "Arıyorum...", "90", "fuzzy"),
]


class TMPage(QWidget):
    """Translation Memory page - MVP with search and sample data."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TMPage")
        
        self._entries = SAMPLE_TM_ENTRIES.copy()
        self._filtered_entries = self._entries.copy()
        
        self._setup_ui()
        self._populate_table()
        logger.debug("TMPage v2 initialized")
    
    def _setup_ui(self):
        """Setup the page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Header / Command Bar
        cmd_layout = QHBoxLayout()
        
        title = SubtitleLabel("Translation Memory")
        cmd_layout.addWidget(title)
        
        cmd_layout.addSpacing(20)
        
        # Actions
        self.create_btn = PushButton("TM Oluştur")
        self.create_btn.setIcon(FIF.ADD)
        self.create_btn.setToolTip("Yakında: Yeni TM veritabanı oluşturma")
        self.create_btn.setEnabled(False)
        cmd_layout.addWidget(self.create_btn)
        
        self.import_btn = PushButton("TMX İçe Aktar")
        self.import_btn.setIcon(FIF.DOWNLOAD)
        self.import_btn.setToolTip("Yakında: TMX dosyalarından içe aktarım")
        self.import_btn.setEnabled(False)
        cmd_layout.addWidget(self.import_btn)
        
        self.export_btn = PushButton("TMX Dışa Aktar")
        self.export_btn.setIcon(FIF.SHARE)
        self.export_btn.setToolTip("Yakında: TMX formatında dışa aktarım")
        self.export_btn.setEnabled(False)
        cmd_layout.addWidget(self.export_btn)
        
        cmd_layout.addStretch()
        layout.addLayout(cmd_layout)
        
        # Info card
        info_card = CardWidget()
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(12, 12, 12, 12)
        
        info_label = BodyLabel(
            "📚 Çeviri Belleği (TM), önceki çevirilerinizi saklar ve yeni metinler için "
            "benzer çevirileri önerir. Aşağıda örnek TM kayıtları gösterilmektedir."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #aaaaaa;")
        info_layout.addWidget(info_label)
        
        layout.addWidget(info_card)
        
        # Search Bar
        search_layout = QHBoxLayout()
        
        self.search_edit = SearchLineEdit()
        self.search_edit.setPlaceholderText("TM'de ara...")
        self.search_edit.setFixedWidth(400)
        self.search_edit.textChanged.connect(self._on_search)
        search_layout.addWidget(self.search_edit)
        
        self.count_label = BodyLabel(f"{len(self._entries)} kayıt")
        self.count_label.setStyleSheet("color: #888888;")
        search_layout.addWidget(self.count_label)
        
        search_layout.addStretch()
        layout.addLayout(search_layout)
        
        # Table
        self.table = TableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Original", "Translation", "Match %", "Source"])
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(3, 100)
        self.table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(TableWidget.SelectionBehavior.SelectRows)
        
        layout.addWidget(self.table)
    
    def _on_search(self, text: str):
        """Filter table based on search text."""
        search_lower = text.lower().strip()
        
        if not search_lower:
            self._filtered_entries = self._entries.copy()
        else:
            self._filtered_entries = [
                entry for entry in self._entries
                if search_lower in entry[0].lower() or search_lower in entry[1].lower()
            ]
        
        self._populate_table()
        self.count_label.setText(f"{len(self._filtered_entries)} / {len(self._entries)} kayıt")
    
    def _populate_table(self):
        """Populate table with filtered entries."""
        self.table.setRowCount(0)
        
        for orig, trans, match, source in self._filtered_entries:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Original
            item_orig = QTableWidgetItem(orig)
            item_orig.setFlags(item_orig.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, item_orig)
            
            # Translation
            item_trans = QTableWidgetItem(trans)
            item_trans.setFlags(item_trans.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, item_trans)
            
            # Match %
            item_match = QTableWidgetItem(f"{match}%")
            item_match.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_match.setFlags(item_match.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 2, item_match)
            
            # Source
            source_icons = {
                "gemini": "🤖",
                "google": "🔄",
                "user": "👤",
                "fuzzy": "❓"
            }
            item_source = QTableWidgetItem(f"{source_icons.get(source, '')} {source}")
            item_source.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_source.setFlags(item_source.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 3, item_source)
