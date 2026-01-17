# -*- coding: utf-8 -*-
"""
RenForge Glossary Page

MVP Implementation (v2):
- Read-only list of glossary terms
- Local search/filter functionality
- Quick Add Term dialog (functional)
- Sample data for demonstration
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QHeaderView, 
    QTableWidgetItem, QDialog, QFormLayout, QLineEdit, QDialogButtonBox
)

from qfluentwidgets import (
    SubtitleLabel, BodyLabel, PushButton, SearchLineEdit, 
    TableWidget, FluentIcon as FIF, CardWidget, MessageBox
)

from renforge_logger import get_logger

logger = get_logger("gui.pages.glossary")


# Sample glossary entries for demonstration
SAMPLE_GLOSSARY = [
    ("MC", "Ana Karakter", "Characters", "Main Character"),
    ("HP", "Can Puanı", "Stats", "Health Points"),
    ("MP", "Büyü Puanı", "Stats", "Magic/Mana Points"),
    ("XP", "Deneyim Puanı", "Stats", "Experience Points"),
    ("NPC", "Oyuncu Olmayan Karakter", "Characters", "Non-Player Character"),
    ("Quest", "Görev", "Gameplay", ""),
    ("Inventory", "Envanter", "UI", ""),
    ("Save", "Kaydet", "UI", ""),
    ("Load", "Yükle", "UI", ""),
    ("Settings", "Ayarlar", "UI", ""),
    ("Continue", "Devam Et", "UI", ""),
    ("New Game", "Yeni Oyun", "UI", ""),
]


class AddTermDialog(QDialog):
    """Simple dialog to add a new glossary term."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Terim Ekle")
        self.setMinimumWidth(400)
        
        layout = QFormLayout(self)
        
        self.term_edit = QLineEdit()
        self.term_edit.setPlaceholderText("Örn: HP")
        layout.addRow("Terim:", self.term_edit)
        
        self.trans_edit = QLineEdit()
        self.trans_edit.setPlaceholderText("Örn: Can Puanı")
        layout.addRow("Çeviri:", self.trans_edit)
        
        self.category_edit = QLineEdit()
        self.category_edit.setPlaceholderText("Örn: Stats")
        layout.addRow("Kategori:", self.category_edit)
        
        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("Opsiyonel açıklama")
        layout.addRow("Notlar:", self.notes_edit)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def get_term_data(self):
        """Return term data tuple."""
        return (
            self.term_edit.text().strip(),
            self.trans_edit.text().strip(),
            self.category_edit.text().strip() or "General",
            self.notes_edit.text().strip()
        )


class GlossaryPage(QWidget):
    """Glossary page - MVP with search and add term functionality."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlossaryPage")
        
        self._entries = list(SAMPLE_GLOSSARY)
        self._filtered_entries = self._entries.copy()
        
        self._setup_ui()
        self._populate_table()
        logger.debug("GlossaryPage v2 initialized")
    
    def _setup_ui(self):
        """Setup the page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Header / Command Bar
        cmd_layout = QHBoxLayout()
        
        title = SubtitleLabel("Glossary (Sözlük)")
        cmd_layout.addWidget(title)
        
        cmd_layout.addSpacing(20)
        
        # Actions
        self.add_btn = PushButton("Terim Ekle")
        self.add_btn.setIcon(FIF.ADD)
        self.add_btn.clicked.connect(self._on_add_term)
        cmd_layout.addWidget(self.add_btn)
        
        self.import_btn = PushButton("CSV İçe Aktar")
        self.import_btn.setIcon(FIF.DOWNLOAD)
        self.import_btn.setToolTip("Yakında: CSV/TBX içe aktarım")
        self.import_btn.setEnabled(False)
        cmd_layout.addWidget(self.import_btn)
        
        self.export_btn = PushButton("CSV Dışa Aktar")
        self.export_btn.setIcon(FIF.SHARE)
        self.export_btn.setToolTip("Yakında: CSV formatında dışa aktarım")
        self.export_btn.setEnabled(False)
        cmd_layout.addWidget(self.export_btn)
        
        cmd_layout.addStretch()
        layout.addLayout(cmd_layout)
        
        # Info card
        info_card = CardWidget()
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(12, 12, 12, 12)
        
        info_label = BodyLabel(
            "📖 Sözlük, tekrarlanan terimlerin tutarlı çevirilerini sağlar. "
            "Karakter isimleri, oyun terimleri ve UI elemanları için kullanılır."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #aaaaaa;")
        info_layout.addWidget(info_label)
        
        layout.addWidget(info_card)
        
        # Search Bar
        search_layout = QHBoxLayout()
        
        self.search_edit = SearchLineEdit()
        self.search_edit.setPlaceholderText("Sözlükte ara...")
        self.search_edit.setFixedWidth(400)
        self.search_edit.textChanged.connect(self._on_search)
        search_layout.addWidget(self.search_edit)
        
        self.count_label = BodyLabel(f"{len(self._entries)} terim")
        self.count_label.setStyleSheet("color: #888888;")
        search_layout.addWidget(self.count_label)
        
        search_layout.addStretch()
        layout.addLayout(search_layout)
        
        # Table
        self.table = TableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Term", "Translation", "Category", "Notes"])
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(2, 120)
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
                if (search_lower in entry[0].lower() or 
                    search_lower in entry[1].lower() or
                    search_lower in entry[2].lower())
            ]
        
        self._populate_table()
        self.count_label.setText(f"{len(self._filtered_entries)} / {len(self._entries)} terim")
    
    def _on_add_term(self):
        """Open add term dialog."""
        dialog = AddTermDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            term_data = dialog.get_term_data()
            
            if not term_data[0] or not term_data[1]:
                MessageBox("Hata", "Terim ve çeviri alanları gereklidir.", self).exec()
                return
            
            # Add to entries
            self._entries.append(term_data)
            self._filtered_entries = self._entries.copy()
            self._populate_table()
            self.count_label.setText(f"{len(self._entries)} terim")
            
            logger.info(f"Added glossary term: {term_data[0]} -> {term_data[1]}")
    
    def _populate_table(self):
        """Populate table with filtered entries."""
        self.table.setRowCount(0)
        
        for term, trans, category, notes in self._filtered_entries:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Term (bold style)
            item_term = QTableWidgetItem(term)
            item_term.setFlags(item_term.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, item_term)
            
            # Translation
            item_trans = QTableWidgetItem(trans)
            item_trans.setFlags(item_trans.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, item_trans)
            
            # Category
            item_cat = QTableWidgetItem(category)
            item_cat.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_cat.setFlags(item_cat.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 2, item_cat)
            
            # Notes
            item_notes = QTableWidgetItem(notes)
            item_notes.setFlags(item_notes.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_notes.setForeground(Qt.GlobalColor.gray)
            self.table.setItem(row, 3, item_notes)
