# -*- coding: utf-8 -*-
"""
RenForge Glossary (Sözlük) Sayfası

GlossaryStore'dan veri okuyarak sözlük terimlerini listeler.
Terim ekleme/silme ve CSV içe/dışa aktarma destekler.
Stage 17: Enabled checkbox, detaylı import özeti, Health jump API.
Stage 18: Enforce Önizleme dialog.
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QHeaderView, 
    QTableWidgetItem, QFileDialog, QDialog, QFormLayout,
    QDialogButtonBox, QCheckBox, QLabel, QTextEdit, QApplication
)
from PySide6.QtGui import QColor, QFont

from qfluentwidgets import (
    SubtitleLabel, BodyLabel, PushButton, SearchLineEdit, 
    TableWidget, FluentIcon as FIF, CardWidget, InfoBar, 
    InfoBarPosition, LineEdit, ComboBox, CheckBox, TextEdit as FluentTextEdit
)

from renforge_logger import get_logger

logger = get_logger("gui.pages.glossary")


class AddTermDialog(QDialog):
    """Yeni sözlük terimi ekleme diyalogu."""
    
    def __init__(self, parent=None, edit_entry=None):
        super().__init__(parent)
        self.edit_entry = edit_entry
        
        title = "Terim Düzenle" if edit_entry else "Terim Ekle"
        self.setWindowTitle(title)
        self.setMinimumWidth(450)
        
        layout = QFormLayout(self)
        
        self.term_edit = LineEdit()
        self.term_edit.setPlaceholderText("Orijinal terim")
        layout.addRow("Terim:", self.term_edit)
        
        self.translation_edit = LineEdit()
        self.translation_edit.setPlaceholderText("Çeviri")
        layout.addRow("Çeviri:", self.translation_edit)
        
        self.category_combo = ComboBox()
        self.category_combo.addItems(["Genel", "UI", "Karakter", "Mekan", "Sistem", "Diğer"])
        # QFluentWidgets ComboBox setEditable desteklemiyor, sabit liste kullanılıyor
        layout.addRow("Kategori:", self.category_combo)
        
        self.notes_edit = LineEdit()
        self.notes_edit.setPlaceholderText("İsteğe bağlı notlar")
        layout.addRow("Notlar:", self.notes_edit)
        
        # Gelişmiş seçenekler
        self.case_sensitive_cb = QCheckBox("Büyük/küçük harf duyarlı")
        layout.addRow("", self.case_sensitive_cb)
        
        self.whole_word_cb = QCheckBox("Tam kelime eşleşmesi")
        self.whole_word_cb.setChecked(True)
        layout.addRow("", self.whole_word_cb)
        
        # Düzenleme modunda mevcut değerleri doldur
        if edit_entry:
            self.term_edit.setText(edit_entry.term_src)
            self.translation_edit.setText(edit_entry.term_dst)
            self.category_combo.setCurrentText(edit_entry.category or "Genel")
            self.notes_edit.setText(edit_entry.notes or "")
            self.case_sensitive_cb.setChecked(edit_entry.case_sensitive)
            self.whole_word_cb.setChecked(edit_entry.whole_word)
        
        # Butonlar
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def get_term_data(self):
        """Terim verilerini döndür."""
        return {
            'term_src': self.term_edit.text().strip(),
            'term_dst': self.translation_edit.text().strip(),
            'category': self.category_combo.currentText().strip(),
            'notes': self.notes_edit.text().strip(),
            'case_sensitive': self.case_sensitive_cb.isChecked(),
            'whole_word': self.whole_word_cb.isChecked()
        }


class EnforcePreviewDialog(QDialog):
    """
    Glossary Enforce Önizleme Dialog (Stage 18 + 18.1)
    
    Kullanıcıya metinleri girmesini ve glossary enforce
    sonuçlarını önizlemesini sağlar.
    
    Stage 18.1 Güncellemeleri:
    - Kopyala ve Çeviriye Uygula butonları ayrıldı
    - Applied terms listesi eklendi
    - Highlight span iyileştirmesi
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Glossary Enforce Önizleme")
        self.setMinimumSize(750, 600)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Kaynak metin
        layout.addWidget(BodyLabel("Kaynak Metin (Original):"))
        self.source_edit = QTextEdit()
        self.source_edit.setPlaceholderText("Orijinal metni buraya yazın...")
        self.source_edit.setMaximumHeight(80)
        layout.addWidget(self.source_edit)
        
        # Mevcut çeviri
        layout.addWidget(BodyLabel("Mevcut Çeviri (Current Translation):"))
        self.target_edit = QTextEdit()
        self.target_edit.setPlaceholderText("Mevcut çeviriyi buraya yazın...")
        self.target_edit.setMaximumHeight(80)
        layout.addWidget(self.target_edit)
        
        # Önizle butonu
        preview_btn = PushButton("Önizle")
        preview_btn.setIcon(FIF.VIEW)
        preview_btn.clicked.connect(self._on_preview)
        layout.addWidget(preview_btn)
        
        # Sonuç özeti
        self.summary_label = BodyLabel("")
        self.summary_label.setStyleSheet("color: #888888; padding: 8px;")
        layout.addWidget(self.summary_label)
        
        # Applied terms listesi (Stage 18.1)
        self.terms_label = BodyLabel("")
        self.terms_label.setWordWrap(True)
        self.terms_label.setStyleSheet("""
            QLabel {
                color: #aaaaaa;
                background-color: #252526;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
            }
        """)
        self.terms_label.setMaximumHeight(100)
        layout.addWidget(self.terms_label)
        
        # Önizleme sonucu
        layout.addWidget(BodyLabel("Önizleme Sonucu (Preview):"))
        self.preview_edit = QTextEdit()
        self.preview_edit.setReadOnly(True)
        self.preview_edit.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d30;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.preview_edit)
        
        # Butonlar (Stage 18.1: ayrı butonlar)
        btn_layout = QHBoxLayout()
        
        # Kopyala butonu
        self.copy_btn = PushButton("Kopyala")
        self.copy_btn.setIcon(FIF.COPY)
        self.copy_btn.setToolTip("Önizleme sonucunu panoya kopyala")
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self._on_copy)
        btn_layout.addWidget(self.copy_btn)
        
        # Çeviriye Uygula butonu
        self.apply_btn = PushButton("Çeviriye Uygula")
        self.apply_btn.setIcon(FIF.ACCEPT)
        self.apply_btn.setToolTip("Mevcut Çeviri alanını önizleme sonucu ile doldur")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._on_apply_to_translation)
        btn_layout.addWidget(self.apply_btn)
        
        btn_layout.addStretch()
        
        close_btn = PushButton("Kapat")
        close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        self._preview_text = ""
        self._last_result = None  # Son önizleme sonucu
    
    def _on_preview(self):
        """Önizleme hesapla ve göster."""
        source = self.source_edit.toPlainText().strip()
        target = self.target_edit.toPlainText().strip()
        
        if not source or not target:
            InfoBar.warning(
                title="Uyarı",
                content="Kaynak metin ve çeviri gerekli",
                parent=self,
                duration=2000,
                position=InfoBarPosition.TOP
            )
            return
        
        try:
            from core.glossary_preview import (
                preview_enforce, format_applied_terms, compute_highlight_spans
            )
            
            result = preview_enforce(source, target)
            self._last_result = result
            
            # Önizleme sonucunu göster
            self._preview_text = result.preview_text
            self.preview_edit.setPlainText(result.preview_text)
            
            # Özet oluştur (kısa versiyon)
            applied_count = result.total_applied
            blocked_count = result.total_blocked
            
            summary_parts = []
            if applied_count > 0:
                summary_parts.append(f"✅ {applied_count} terim uygulandı")
            else:
                summary_parts.append("ℹ️ Uygulanacak terim yok")
            
            if blocked_count > 0:
                blocked_list = ", ".join(result.blocked_segments[:3])
                if len(result.blocked_segments) > 3:
                    blocked_list += f" (+{len(result.blocked_segments) - 3})"
                summary_parts.append(f"🛡️ {blocked_count} placeholder korundu: {blocked_list}")
            
            self.summary_label.setText(" | ".join(summary_parts))
            
            # Applied terms listesi (Stage 18.1)
            terms_text = format_applied_terms(result.applied_terms, max_items=20)
            self.terms_label.setText(terms_text)
            
            # Butonları etkinleştir
            self.copy_btn.setEnabled(True)
            self.apply_btn.setEnabled(True)
            
        except Exception as e:
            logger.error(f"Preview failed: {e}")
            InfoBar.error(
                title="Hata",
                content=f"Önizleme hatası: {e}",
                parent=self,
                duration=3000,
                position=InfoBarPosition.TOP
            )
    
    def _on_copy(self):
        """Önizleme sonucunu clipboard'a kopyala."""
        if self._preview_text:
            clipboard = QApplication.clipboard()
            clipboard.setText(self._preview_text)
            InfoBar.success(
                title="Kopyalandı",
                content="Önizleme sonucu panoya kopyalandı",
                parent=self,
                duration=2000,
                position=InfoBarPosition.TOP
            )
    
    def _on_apply_to_translation(self):
        """Önizleme sonucunu Mevcut Çeviri alanına uygula (Stage 18.1)."""
        if self._preview_text:
            self.target_edit.setPlainText(self._preview_text)
            InfoBar.success(
                title="Uygulandı",
                content="Önizleme sonucu çeviri alanına uygulandı",
                parent=self,
                duration=2000,
                position=InfoBarPosition.TOP
            )



class GlossaryPage(QWidget):
    """Sözlük sayfası - GlossaryStore'a bağlı."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlossaryPage")
        
        self._entries = []  # GlossaryEntry listesi
        self._filtered_entries = []
        
        self._setup_ui()
        self._load_from_store()
        logger.debug("GlossaryPage initialized with GlossaryStore")
    
    def _setup_ui(self):
        """Sayfa arayüzünü oluştur."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Header / Command Bar
        cmd_layout = QHBoxLayout()
        
        title = SubtitleLabel("Sözlük (Glossary)")
        cmd_layout.addWidget(title)
        
        cmd_layout.addSpacing(20)
        
        # Aksiyonlar
        self.add_btn = PushButton("Terim Ekle")
        self.add_btn.setIcon(FIF.ADD)
        self.add_btn.clicked.connect(self._on_add_term)
        cmd_layout.addWidget(self.add_btn)
        
        self.edit_btn = PushButton("Düzenle")
        self.edit_btn.setIcon(FIF.EDIT)
        self.edit_btn.clicked.connect(self._on_edit_term)
        cmd_layout.addWidget(self.edit_btn)
        
        self.delete_btn = PushButton("Sil")
        self.delete_btn.setIcon(FIF.DELETE)
        self.delete_btn.clicked.connect(self._on_delete_term)
        cmd_layout.addWidget(self.delete_btn)
        
        self.import_btn = PushButton("CSV İçe Aktar")
        self.import_btn.setIcon(FIF.DOWNLOAD)
        self.import_btn.clicked.connect(self._on_import_csv)
        cmd_layout.addWidget(self.import_btn)
        
        self.export_btn = PushButton("CSV Dışa Aktar")
        self.export_btn.setIcon(FIF.SHARE)
        self.export_btn.clicked.connect(self._on_export_csv)
        cmd_layout.addWidget(self.export_btn)
        
        self.refresh_btn = PushButton("Yenile")
        self.refresh_btn.setIcon(FIF.SYNC)
        self.refresh_btn.clicked.connect(self._load_from_store)
        cmd_layout.addWidget(self.refresh_btn)
        
        # Stage 18: Enforce Önizleme butonu
        self.preview_btn = PushButton("Önizle")
        self.preview_btn.setIcon(FIF.VIEW)
        self.preview_btn.setToolTip("Glossary Enforce Önizleme")
        self.preview_btn.clicked.connect(self._on_enforce_preview)
        cmd_layout.addWidget(self.preview_btn)
        
        cmd_layout.addStretch()
        layout.addLayout(cmd_layout)
        
        # Bilgi kartı
        info_card = CardWidget()
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(12, 12, 12, 12)
        
        info_label = BodyLabel(
            "📖 Sözlük, çevirilerde tutarlılık sağlamak için terim eşlemelerini tanımlar. "
            "Çeviri sırasında bu terimler kontrol edilir ve eksikler QC olarak raporlanır."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #aaaaaa;")
        info_layout.addWidget(info_label)
        
        layout.addWidget(info_card)
        
        # Arama Çubuğu
        search_layout = QHBoxLayout()
        
        self.search_edit = SearchLineEdit()
        self.search_edit.setPlaceholderText("Sözlükte ara...")
        self.search_edit.setFixedWidth(400)
        self.search_edit.textChanged.connect(self._on_search)
        search_layout.addWidget(self.search_edit)
        
        self.count_label = BodyLabel("0 terim")
        self.count_label.setStyleSheet("color: #888888;")
        search_layout.addWidget(self.count_label)
        
        search_layout.addStretch()
        layout.addLayout(search_layout)
        
        # Tablo - Stage 17: Enabled kolonu eklendi
        self.table = TableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Enabled", "Term", "Translation", "Category", "Notes"])
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 70)
        self.table.setColumnWidth(3, 100)
        self.table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(TableWidget.SelectionBehavior.SelectRows)
        self.table.cellClicked.connect(self._on_cell_clicked)
        
        layout.addWidget(self.table)
    
    def _load_from_store(self):
        """GlossaryStore'dan verileri yükle."""
        try:
            from core.glossary_store import GlossaryStore
            
            store = GlossaryStore.instance()
            self._entries = store.list_all(include_disabled=True)
            self._filtered_entries = self._entries.copy()
            self._populate_table()
            self.count_label.setText(f"{len(self._entries)} terim")
            
        except Exception as e:
            logger.error(f"GlossaryStore yüklenemedi: {e}")
            self._entries = []
            self._filtered_entries = []
            self._populate_table()
    
    def _on_search(self, text: str):
        """Arama metnine göre tabloyu filtrele."""
        search_lower = text.lower().strip()
        
        if not search_lower:
            self._filtered_entries = self._entries.copy()
        else:
            self._filtered_entries = [
                e for e in self._entries
                if search_lower in e.term_src.lower() or 
                   search_lower in e.term_dst.lower() or
                   search_lower in e.category.lower()
            ]
        
        self._populate_table()
        self.count_label.setText(f"{len(self._filtered_entries)} / {len(self._entries)} terim")
    
    def _populate_table(self):
        """Tabloyu filtreli girdilerle doldur."""
        self.table.setRowCount(0)
        
        for entry in self._filtered_entries:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Enabled checkbox
            item_enabled = QTableWidgetItem()
            item_enabled.setCheckState(Qt.CheckState.Checked if entry.enabled else Qt.CheckState.Unchecked)
            item_enabled.setData(Qt.ItemDataRole.UserRole, entry.id)  # ID'yi sakla
            item_enabled.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, item_enabled)
            
            # Term (source)
            item_term = QTableWidgetItem(entry.term_src)
            item_term.setFlags(item_term.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_term.setData(Qt.ItemDataRole.UserRole, entry.id)
            self.table.setItem(row, 1, item_term)
            
            # Translation (target)
            item_trans = QTableWidgetItem(entry.term_dst)
            item_trans.setFlags(item_trans.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 2, item_trans)
            
            # Category
            item_cat = QTableWidgetItem(entry.category or "Genel")
            item_cat.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_cat.setFlags(item_cat.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 3, item_cat)
            
            # Notes
            item_notes = QTableWidgetItem(entry.notes or "")
            item_notes.setFlags(item_notes.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 4, item_notes)
    
    def _on_cell_clicked(self, row: int, col: int):
        """Hücre tıklandığında - Enabled toggle için."""
        if col == 0:  # Enabled kolonu
            item = self.table.item(row, 0)
            if item:
                entry_id = item.data(Qt.ItemDataRole.UserRole)
                new_state = item.checkState() == Qt.CheckState.Checked
                
                try:
                    from core.glossary_store import GlossaryStore
                    store = GlossaryStore.instance()
                    store.update(entry_id, enabled=new_state)
                    logger.debug(f"Glossary entry {entry_id} enabled={new_state}")
                except Exception as e:
                    logger.error(f"Enable toggle failed: {e}")
    
    def _on_add_term(self):
        """Terim ekleme diyalogunu aç."""
        dialog = AddTermDialog(self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_term_data()
            
            if not data['term_src'] or not data['term_dst']:
                InfoBar.warning(
                    title="Uyarı",
                    content="Terim ve çeviri alanları boş olamaz",
                    parent=self,
                    duration=3000,
                    position=InfoBarPosition.TOP
                )
                return
            
            try:
                from core.glossary_store import GlossaryStore
                
                store = GlossaryStore.instance()
                entry_id = store.insert(
                    term_src=data['term_src'],
                    term_dst=data['term_dst'],
                    category=data['category'],
                    notes=data['notes'],
                    case_sensitive=data['case_sensitive'],
                    whole_word=data['whole_word']
                )
                
                InfoBar.success(
                    title="Terim Eklendi",
                    content=f"'{data['term_src']}' → '{data['term_dst']}'",
                    parent=self,
                    duration=2000,
                    position=InfoBarPosition.TOP
                )
                self._load_from_store()
                
            except Exception as e:
                logger.error(f"Terim eklenemedi: {e}")
                InfoBar.error(
                    title="Hata",
                    content=f"Terim eklenemedi: {e}",
                    parent=self,
                    duration=3000,
                    position=InfoBarPosition.TOP
                )
    
    def _on_edit_term(self):
        """Seçili terimi düzenle."""
        selected_rows = self.table.selectionModel().selectedRows()
        
        if not selected_rows:
            InfoBar.warning(
                title="Uyarı",
                content="Lütfen düzenlenecek terimi seçin",
                parent=self,
                duration=2000,
                position=InfoBarPosition.TOP
            )
            return
        
        row = selected_rows[0].row()
        item = self.table.item(row, 1)  # Term kolonu
        if not item:
            return
        
        entry_id = item.data(Qt.ItemDataRole.UserRole)
        
        # Entry'yi bul
        entry = next((e for e in self._entries if e.id == entry_id), None)
        if not entry:
            return
        
        dialog = AddTermDialog(self, edit_entry=entry)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_term_data()
            
            try:
                from core.glossary_store import GlossaryStore
                
                store = GlossaryStore.instance()
                store.update(
                    entry_id,
                    term_src=data['term_src'],
                    term_dst=data['term_dst'],
                    category=data['category'],
                    notes=data['notes'],
                    case_sensitive=data['case_sensitive'],
                    whole_word=data['whole_word']
                )
                
                InfoBar.success(
                    title="Terim Güncellendi",
                    content=f"'{data['term_src']}'",
                    parent=self,
                    duration=2000,
                    position=InfoBarPosition.TOP
                )
                self._load_from_store()
                
            except Exception as e:
                logger.error(f"Terim güncellenemedi: {e}")
                InfoBar.error(
                    title="Hata",
                    content=f"Güncelleme hatası: {e}",
                    parent=self,
                    duration=3000,
                    position=InfoBarPosition.TOP
                )
    
    def _on_delete_term(self):
        """Seçili terimi sil."""
        selected_rows = self.table.selectionModel().selectedRows()
        
        if not selected_rows:
            InfoBar.warning(
                title="Uyarı",
                content="Lütfen silinecek terimi seçin",
                parent=self,
                duration=2000,
                position=InfoBarPosition.TOP
            )
            return
        
        try:
            from core.glossary_store import GlossaryStore
            
            store = GlossaryStore.instance()
            deleted = 0
            
            for model_index in selected_rows:
                item = self.table.item(model_index.row(), 1)
                if item:
                    entry_id = item.data(Qt.ItemDataRole.UserRole)
                    if entry_id and store.delete(entry_id):
                        deleted += 1
            
            if deleted > 0:
                InfoBar.success(
                    title="Silindi",
                    content=f"{deleted} terim silindi",
                    parent=self,
                    duration=2000,
                    position=InfoBarPosition.TOP
                )
                self._load_from_store()
                
        except Exception as e:
            logger.error(f"Terim silinemedi: {e}")
            InfoBar.error(
                title="Hata",
                content=f"Silme hatası: {e}",
                parent=self,
                duration=3000,
                position=InfoBarPosition.TOP
            )
    
    def _on_import_csv(self):
        """CSV dosyasından içe aktar."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "CSV Dosyası Seç",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            from core.glossary_csv import import_to_glossary_store
            
            result = import_to_glossary_store(file_path)
            
            # Stage 17: Detaylı özet
            summary = f"Eklenen: {result['added']}, Güncellenen: {result['updated']}, Atlanan: {result['skipped']}"
            
            if result['added'] > 0 or result['updated'] > 0:
                InfoBar.success(
                    title="İçe Aktarma Başarılı",
                    content=summary,
                    parent=self,
                    duration=4000,
                    position=InfoBarPosition.TOP
                )
                self._load_from_store()
            else:
                InfoBar.warning(
                    title="İçe Aktarma",
                    content=f"Hiç yeni terim yok. {summary}",
                    parent=self,
                    duration=4000,
                    position=InfoBarPosition.TOP
                )
                
        except Exception as e:
            logger.error(f"CSV import failed: {e}")
            InfoBar.error(
                title="Hata",
                content=f"İçe aktarma hatası: {e}",
                parent=self,
                duration=3000,
                position=InfoBarPosition.TOP
            )
    
    def _on_export_csv(self):
        """CSV dosyasına dışa aktar."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "CSV Dosyası Kaydet",
            "renforge_glossary.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            from core.glossary_csv import export_from_glossary_store
            
            exported = export_from_glossary_store(file_path)
            
            if exported > 0:
                InfoBar.success(
                    title="Dışa Aktarma Başarılı",
                    content=f"{exported} terim dışa aktarıldı",
                    parent=self,
                    duration=3000,
                    position=InfoBarPosition.TOP
                )
            else:
                InfoBar.warning(
                    title="Dışa Aktarma",
                    content="Dışa aktarılacak terim yok",
                    parent=self,
                    duration=3000,
                    position=InfoBarPosition.TOP
                )
                
        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            InfoBar.error(
                title="Hata",
                content=f"Dışa aktarma hatası: {e}",
                parent=self,
                duration=3000,
                position=InfoBarPosition.TOP
            )
    
    # =========================================================================
    # HEALTH JUMP API (Stage 17)
    # =========================================================================
    
    def search_and_select(self, search_text: str):
        """
        Arama kutusuna metin yaz, ara ve ilk sonucu seç.
        Health OPEN_IN_GLOSSARY aksiyonu için.
        """
        self.search_edit.setText(search_text)
        self._on_search(search_text)
        
        if self.table.rowCount() > 0:
            self.table.selectRow(0)
            self._flash_row(0)
    
    def _flash_row(self, row: int, color: QColor = None):
        """Satırı kısa süreliğine vurgula (flash effect)."""
        if color is None:
            color = QColor(100, 149, 237, 100)  # Cornflower blue
        
        # Satırdaki tüm hücreleri vurgula
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                original_bg = item.background()
                item.setBackground(color)
                
                # 500ms sonra eski renge dön
                QTimer.singleShot(500, lambda i=item, bg=original_bg: i.setBackground(bg))
    
    # =========================================================================
    # STAGE 18: ENFORCE PREVIEW
    # =========================================================================
    
    def _on_enforce_preview(self):
        """Enforce önizleme dialog'unu aç."""
        dialog = EnforcePreviewDialog(self)
        dialog.exec()
