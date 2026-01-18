# -*- coding: utf-8 -*-
"""
RenForge TM (Translation Memory) Sayfası

TMStore'dan veri okuyarak TM girdilerini listeler.
TMX içe/dışa aktarma destekler.
Stage 17: Use Count, Last Used kolonları ve dil filtresi eklendi.
Stage 19: Import conflict strategy seçimi eklendi.
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QHeaderView, 
    QTableWidgetItem, QFileDialog, QDialog, QFormLayout,
    QDialogButtonBox, QButtonGroup, QRadioButton
)
from PySide6.QtGui import QColor

from qfluentwidgets import (
    SubtitleLabel, BodyLabel, PushButton, SearchLineEdit, 
    TableWidget, FluentIcon as FIF, CardWidget, InfoBar, 
    InfoBarPosition, SwitchButton
)

from renforge_logger import get_logger

logger = get_logger("gui.pages.tm")


class TMPage(QWidget):
    """Translation Memory sayfası - TMStore'a bağlı."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TMPage")
        
        self._entries = []  # TM girdileri
        self._filtered_entries = []
        self._all_langs = False  # Tüm diller toggle
        
        self._setup_ui()
        self._load_from_store()
        logger.debug("TMPage initialized with TMStore")
    
    def _setup_ui(self):
        """Sayfa arayüzünü oluştur."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Header / Command Bar
        cmd_layout = QHBoxLayout()
        
        title = SubtitleLabel("Translation Memory")
        cmd_layout.addWidget(title)
        
        cmd_layout.addSpacing(20)
        
        # Aksiyonlar
        self.import_btn = PushButton("TMX İçe Aktar")
        self.import_btn.setIcon(FIF.DOWNLOAD)
        self.import_btn.setToolTip("TMX dosyasından içe aktar")
        self.import_btn.clicked.connect(self._on_import_tmx)
        cmd_layout.addWidget(self.import_btn)
        
        self.export_btn = PushButton("TMX Dışa Aktar")
        self.export_btn.setIcon(FIF.SHARE)
        self.export_btn.setToolTip("TMX formatında dışa aktar")
        self.export_btn.clicked.connect(self._on_export_tmx)
        cmd_layout.addWidget(self.export_btn)
        
        # Stage 20: Düzenle butonu
        self.edit_btn = PushButton("Düzenle")
        self.edit_btn.setIcon(FIF.EDIT)
        self.edit_btn.setToolTip("Seçili girdiyi düzenle")
        self.edit_btn.clicked.connect(self._on_edit_entry)
        cmd_layout.addWidget(self.edit_btn)
        
        # Stage 20: Sil butonu
        self.delete_btn = PushButton("Sil")
        self.delete_btn.setIcon(FIF.DELETE)
        self.delete_btn.setToolTip("Seçili girdiyi sil")
        self.delete_btn.clicked.connect(self._on_delete_entry)
        cmd_layout.addWidget(self.delete_btn)
        
        self.refresh_btn = PushButton("Yenile")
        self.refresh_btn.setIcon(FIF.SYNC)
        self.refresh_btn.clicked.connect(self._load_from_store)
        cmd_layout.addWidget(self.refresh_btn)
        
        cmd_layout.addStretch()
        layout.addLayout(cmd_layout)
        
        # Bilgi kartı
        info_card = CardWidget()
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(12, 12, 12, 12)
        
        info_label = BodyLabel(
            "📚 Çeviri Belleği (TM), önceki çevirilerinizi saklar ve yeni metinler için "
            "benzer çevirileri önerir. Aşağıda kayıtlı TM girdileri gösterilmektedir."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #aaaaaa;")
        info_layout.addWidget(info_label)
        
        layout.addWidget(info_card)
        
        # Arama ve Filtre Çubuğu
        search_layout = QHBoxLayout()
        
        self.search_edit = SearchLineEdit()
        self.search_edit.setPlaceholderText("TM'de ara...")
        self.search_edit.setFixedWidth(400)
        self.search_edit.textChanged.connect(self._on_search)
        search_layout.addWidget(self.search_edit)
        
        # Dil filtresi toggle
        self.lang_label = BodyLabel("Aktif Dil Çifti")
        self.lang_label.setStyleSheet("color: #888888;")
        search_layout.addWidget(self.lang_label)
        
        self.all_langs_switch = SwitchButton()
        self.all_langs_switch.setChecked(False)
        self.all_langs_switch.setToolTip("Tüm dil çiftlerini göster")
        self.all_langs_switch.checkedChanged.connect(self._on_lang_filter_changed)
        search_layout.addWidget(self.all_langs_switch)
        
        self.all_langs_label = BodyLabel("Tüm Diller")
        self.all_langs_label.setStyleSheet("color: #888888;")
        search_layout.addWidget(self.all_langs_label)
        
        search_layout.addSpacing(20)
        
        self.count_label = BodyLabel("0 kayıt")
        self.count_label.setStyleSheet("color: #888888;")
        search_layout.addWidget(self.count_label)
        
        search_layout.addStretch()
        layout.addLayout(search_layout)
        
        # Tablo - Stage 17: Use Count ve Last Used eklendi
        self.table = TableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Original", "Translation", "Match %", "Source", "Use Count", "Last Used"
        ])
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 70)
        self.table.setColumnWidth(3, 90)
        self.table.setColumnWidth(4, 70)
        self.table.setColumnWidth(5, 140)
        self.table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(TableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(TableWidget.SelectionMode.ExtendedSelection)  # Çoklu seçim
        
        layout.addWidget(self.table)
    
    def _get_lang_pair(self):
        """Aktif dil çiftini ayarlardan al."""
        try:
            from models.settings_model import SettingsModel
            settings = SettingsModel.instance()
            return (
                getattr(settings, 'source_lang', 'en') or 'en',
                getattr(settings, 'target_lang', 'tr') or 'tr'
            )
        except:
            return ('en', 'tr')
    
    def _load_from_store(self):
        """TMStore'dan verileri yükle."""
        try:
            from core.tm_store import TMStore
            
            tm = TMStore.instance()
            conn = tm._get_connection()
            
            # Dil filtresi
            source_lang, target_lang = self._get_lang_pair()
            
            if self._all_langs:
                cursor = conn.execute("""
                    SELECT id, source_text, target_text, origin, use_count, updated_at,
                           source_lang, target_lang
                    FROM tm_entries 
                    ORDER BY use_count DESC, updated_at DESC
                    LIMIT 1000
                """)
            else:
                cursor = conn.execute("""
                    SELECT id, source_text, target_text, origin, use_count, updated_at,
                           source_lang, target_lang
                    FROM tm_entries 
                    WHERE source_lang = ? AND target_lang = ?
                    ORDER BY use_count DESC, updated_at DESC
                    LIMIT 1000
                """, (source_lang, target_lang))
            
            self._entries = []
            for row in cursor.fetchall():
                self._entries.append({
                    'id': row['id'],  # Stage 20: ID eklendi
                    'source': row['source_text'],
                    'target': row['target_text'],
                    'origin': row['origin'] or 'unknown',
                    'use_count': row['use_count'],
                    'updated_at': row['updated_at'] or '',
                    'source_lang': row['source_lang'],
                    'target_lang': row['target_lang']
                })
            
            self._filtered_entries = self._entries.copy()
            self._populate_table()
            
            lang_info = f" ({source_lang}→{target_lang})" if not self._all_langs else " (Tümü)"
            self.count_label.setText(f"{len(self._entries)} kayıt{lang_info}")
            
        except Exception as e:
            logger.error(f"TMStore yüklenemedi: {e}")
            self._entries = []
            self._filtered_entries = []
            self._populate_table()
    
    def _on_lang_filter_changed(self, checked: bool):
        """Dil filtresi değiştiğinde."""
        self._all_langs = checked
        self._load_from_store()
    
    def _on_search(self, text: str):
        """Arama metnine göre tabloyu filtrele."""
        search_lower = text.lower().strip()
        
        if not search_lower:
            self._filtered_entries = self._entries.copy()
        else:
            self._filtered_entries = [
                e for e in self._entries
                if search_lower in e['source'].lower() or search_lower in e['target'].lower()
            ]
        
        self._populate_table()
        self.count_label.setText(f"{len(self._filtered_entries)} / {len(self._entries)} kayıt")
    
    def _populate_table(self):
        """Tabloyu filtreli girdilerle doldur."""
        self.table.setRowCount(0)
        
        source_icons = {
            "gemini": "🤖",
            "google": "🔄",
            "user": "👤",
            "manual": "✏️",
            "tmx_import": "📥",
            "unknown": "❓"
        }
        
        for entry in self._filtered_entries:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Original
            item_orig = QTableWidgetItem(entry['source'])
            item_orig.setFlags(item_orig.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, item_orig)
            
            # Translation
            item_trans = QTableWidgetItem(entry['target'])
            item_trans.setFlags(item_trans.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, item_trans)
            
            # Match % - Exact match için her zaman 100%
            item_match = QTableWidgetItem("100%")
            item_match.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_match.setFlags(item_match.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 2, item_match)
            
            # Source
            origin = entry['origin']
            icon = source_icons.get(origin, source_icons['unknown'])
            item_source = QTableWidgetItem(f"{icon} {origin}")
            item_source.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_source.setFlags(item_source.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 3, item_source)
            
            # Use Count
            item_count = QTableWidgetItem(str(entry['use_count']))
            item_count.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_count.setFlags(item_count.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 4, item_count)
            
            # Last Used (updated_at'ın okunabilir hali)
            last_used = entry['updated_at'][:16].replace("T", " ") if entry['updated_at'] else "-"
            item_last = QTableWidgetItem(last_used)
            item_last.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_last.setFlags(item_last.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 5, item_last)
    
    def _on_import_tmx(self):
        """TMX dosyasından içe aktar (Stage 19: Strategy seçimi ile)."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "TMX Dosyası Seç",
            "",
            "TMX Files (*.tmx);;All Files (*)"
        )
        
        if not file_path:
            return
        
        # Strategy seçim dialog'u
        strategy = self._show_import_strategy_dialog(is_tm=True)
        if not strategy:
            return  # İptal edildi
        
        try:
            from core.tm_tmx import import_to_tm_store
            
            source_lang, target_lang = self._get_lang_pair()
            result = import_to_tm_store(file_path, target_lang, source_lang, strategy=strategy)
            
            # Stage 19: Çakışma sayısı dahil özet
            conflicts = result.get('conflicts', 0)
            summary = f"Eklenen: {result['added']}, Güncellenen: {result['updated']}, Atlanan: {result['skipped']}"
            if conflicts > 0:
                summary += f", Çakışma: {conflicts}"
            
            if result['added'] > 0 or result['updated'] > 0:
                InfoBar.success(
                    title="İçe Aktarma Başarılı",
                    content=summary,
                    parent=self,
                    duration=4000,
                    position=InfoBarPosition.TOP
                )
                self._load_from_store()  # Listeyi yenile
            else:
                InfoBar.warning(
                    title="İçe Aktarma",
                    content=f"Hiç yeni girdi yok. {summary}",
                    parent=self,
                    duration=4000,
                    position=InfoBarPosition.TOP
                )
                
        except Exception as e:
            logger.error(f"TMX import failed: {e}")
            InfoBar.error(
                title="Hata",
                content=f"İçe aktarma hatası: {e}",
                parent=self,
                duration=3000,
                position=InfoBarPosition.TOP
            )
    
    def _show_import_strategy_dialog(self, is_tm: bool = True) -> str:
        """
        Import strategy seçim dialog'unu göster.
        
        Args:
            is_tm: TM import ise True (keep_higher_usecount seçeneği göster)
        
        Returns:
            Seçilen strategy veya None (iptal)
        """
        dialog = QDialog(self)
        dialog.setWindowTitle("İçe Aktarma Stratejisi")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        # Açıklama
        desc = BodyLabel(
            "Mevcut kayıtlarla çakışan girdiler için nasıl davranılsın?"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Radio butonlar
        button_group = QButtonGroup(dialog)
        
        strategies = [
            ("skip", "Atla (Mevcut kaydı koru)"),
            ("overwrite", "Üzerine Yaz (Gelen ile değiştir)"),
            ("keep_newest", "En Yeniyi Tut (Timestamp'e göre)"),
        ]
        
        if is_tm:
            strategies.append(("keep_higher_usecount", "En Çok Kullanılanı Tut (Use Count)"))
        
        radios = []
        for i, (value, label) in enumerate(strategies):
            radio = QRadioButton(label)
            radio.setProperty("strategy_value", value)
            if i == 0:
                radio.setChecked(True)
            button_group.addButton(radio, i)
            layout.addWidget(radio)
            radios.append(radio)
        
        # Butonlar
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            for radio in radios:
                if radio.isChecked():
                    return radio.property("strategy_value")
            return "skip"  # Default
        
        return None  # İptal
    
    def _on_export_tmx(self):
        """TMX dosyasına dışa aktar."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "TMX Dosyası Kaydet",
            "renforge_tm.tmx",
            "TMX Files (*.tmx);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            from core.tm_tmx import export_from_tm_store
            
            source_lang, target_lang = self._get_lang_pair()
            exported = export_from_tm_store(file_path, source_lang, target_lang)
            
            if exported > 0:
                InfoBar.success(
                    title="Dışa Aktarma Başarılı",
                    content=f"{exported} girdi dışa aktarıldı",
                    parent=self,
                    duration=3000,
                    position=InfoBarPosition.TOP
                )
            else:
                InfoBar.warning(
                    title="Dışa Aktarma",
                    content="Dışa aktarılacak girdi yok",
                    parent=self,
                    duration=3000,
                    position=InfoBarPosition.TOP
                )
                
        except Exception as e:
            logger.error(f"TMX export failed: {e}")
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
        Health OPEN_IN_TM aksiyonu için.
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
    # STAGE 20: DÜZENLE / SİL
    # =========================================================================
    
    def _on_edit_entry(self):
        """Seçili TM girdisini düzenle (Stage 20.1: Gelişmiş dialog)."""
        selected_rows = self.table.selectionModel().selectedRows()
        
        if not selected_rows:
            InfoBar.warning(
                title="Uyarı",
                content="Lütfen düzenlenecek girdiyi seçin",
                parent=self,
                duration=2000,
                position=InfoBarPosition.TOP
            )
            return
        
        row = selected_rows[0].row()
        if row >= len(self._filtered_entries):
            return
        
        entry = self._filtered_entries[row]
        entry_id = entry.get('id')  # Seçimi korumak için
        
        # Düzenleme dialog'u (Stage 20.1: Gelişmiş)
        dialog = QDialog(self)
        dialog.setWindowTitle("TM Girdisini Düzenle")
        dialog.setMinimumWidth(600)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        
        # Bilgi kartı (Stage 20.1)
        info_card = CardWidget()
        info_layout = QHBoxLayout(info_card)
        info_layout.setContentsMargins(12, 8, 12, 8)
        
        lang_info = f"{entry.get('source_lang', 'en')} → {entry.get('target_lang', 'tr')}"
        origin_icon = {"gemini": "🤖", "google": "🔄", "user": "👤", "manual": "✏️"}.get(entry['origin'], "❓")
        use_count = entry.get('use_count', 0)
        last_used = entry.get('updated_at', '')[:10] if entry.get('updated_at') else '-'
        
        info_text = f"📌 {lang_info}  |  {origin_icon} {entry['origin']}  |  🔢 {use_count} kullanım  |  📅 {last_used}"
        info_label = BodyLabel(info_text)
        info_label.setStyleSheet("color: #888888;")
        info_layout.addWidget(info_label)
        layout.addWidget(info_card)
        
        # Kaynak metin (salt okunur, kopyalanabilir)
        layout.addWidget(BodyLabel("Kaynak Metin (Kopyalanabilir):"))
        from qfluentwidgets import TextEdit
        source_edit = TextEdit()
        source_edit.setPlainText(entry['source'])
        source_edit.setReadOnly(True)
        source_edit.setMaximumHeight(80)
        source_edit.setStyleSheet("QTextEdit { background-color: #252526; }")
        layout.addWidget(source_edit)
        
        # Çeviri (düzenlenebilir)
        layout.addWidget(BodyLabel("Çeviri (Düzenlenebilir):"))
        target_edit = TextEdit()
        target_edit.setPlainText(entry['target'])
        target_edit.setMaximumHeight(100)
        layout.addWidget(target_edit)
        
        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = PushButton("Vazgeç")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = PushButton("Kaydet")
        save_btn.setIcon(FIF.SAVE)
        save_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_target = target_edit.toPlainText().strip()
            if new_target and new_target != entry['target']:
                try:
                    from core.tm_store import TMStore
                    tm = TMStore.instance()
                    if tm.update(entry_id, target_text=new_target):
                        InfoBar.success(
                            title="Güncellendi",
                            content="TM girdisi güncellendi",
                            parent=self,
                            duration=2000,
                            position=InfoBarPosition.TOP
                        )
                        # Tabloyu yenile ve seçimi koru
                        self._load_from_store()
                        self._select_entry_by_id(entry_id)
                except Exception as e:
                    logger.error(f"TM update failed: {e}")
                    InfoBar.error(
                        title="Hata",
                        content=f"Güncelleme hatası: {e}",
                        parent=self,
                        duration=3000,
                        position=InfoBarPosition.TOP
                    )
    
    def _select_entry_by_id(self, entry_id: int):
        """ID'ye göre tablodan entry'yi seç (Stage 20.1)."""
        for i, entry in enumerate(self._filtered_entries):
            if entry.get('id') == entry_id:
                self.table.selectRow(i)
                self.table.scrollTo(self.table.model().index(i, 0))
                return
    
    def _select_next_row(self, deleted_row: int):
        """Silinen satırdan sonra mantıklı satıra odaklan (Stage 20.1)."""
        if self.table.rowCount() == 0:
            return
        
        # Silinen satır veya bir önceki
        next_row = min(deleted_row, self.table.rowCount() - 1)
        self.table.selectRow(next_row)
    
    def _on_delete_entry(self):
        """Seçili TM girdisini/girdilerini sil."""
        selected_rows = self.table.selectionModel().selectedRows()
        
        if not selected_rows:
            InfoBar.warning(
                title="Uyarı",
                content="Lütfen silinecek girdiyi seçin",
                parent=self,
                duration=2000,
                position=InfoBarPosition.TOP
            )
            return
        
        # Onay dialog'u
        count = len(selected_rows)
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Silme Onayı",
            f"{count} TM girdisini silmek istediğinizden emin misiniz?\n\nBu işlem geri alınamaz.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            from core.tm_store import TMStore
            tm = TMStore.instance()
            deleted = 0
            
            for model_index in selected_rows:
                row = model_index.row()
                if row < len(self._filtered_entries):
                    entry_id = self._filtered_entries[row].get('id')
                    if entry_id and tm.delete(entry_id):
                        deleted += 1
                        first_deleted_row = min(first_deleted_row, row) if 'first_deleted_row' in dir() else row
            
            # İlk silinen satırı kaydet
            first_deleted_row = selected_rows[0].row() if selected_rows else 0
            
            if deleted > 0:
                InfoBar.success(
                    title="Silindi",
                    content=f"{deleted} girdi silindi",
                    parent=self,
                    duration=2000,
                    position=InfoBarPosition.TOP
                )
                self._load_from_store()
                # Silme sonrası mantıklı satıra odaklan (Stage 20.1)
                self._select_next_row(first_deleted_row)
                
        except Exception as e:
            logger.error(f"TM delete failed: {e}")
            InfoBar.error(
                title="Hata",
                content=f"Silme hatası: {e}",
                parent=self,
                duration=3000,
                position=InfoBarPosition.TOP
            )
