# -*- coding: utf-8 -*-
"""
TranslationTableView - Performans için Optimize Edilmiş QTableView

Bu view, büyük veri setleri için optimize edilmiştir.
Virtual scrolling sayesinde sadece görünen satırlar render edilir.

PERFORMANS AYARLARI:
- setWordWrap(False): Word wrap çok yavaş
- setUniformRowHeights(True): Tek tip satır yüksekliği
- ResizeToContents KULLANILMAZ: Her satır için ölçüm yapar
"""

from typing import Optional, List

from PyQt6.QtWidgets import (
    QTableView, QHeaderView, QAbstractItemView, QApplication, QMenu
)
from PyQt6.QtCore import Qt, QModelIndex, pyqtSignal
from PyQt6.QtGui import QKeySequence, QAction, QClipboard

from renforge_logger import get_logger

logger = get_logger("gui.views.table_view")


class TranslationTableView(QTableView):
    """
    Çeviri tablosu için optimize edilmiş view.
    
    NEDEN DONMUYOR:
    1. Virtual scrolling: Sadece görünen satırlar render edilir
    2. UniformRowHeights: Satır yüksekliği hesabı yapılmaz
    3. WordWrap kapalı: Kelime sarma hesabı yok
    4. ResizeToContents yok: Sütun genişliği otomatik hesaplanmaz
    
    ÖZELLİKLER:
    - Ctrl+C ile seçili satırları panoya kopyala (TSV formatı)
    - Sağ tık context menu
    - Satır seçimi modu
    - Genişletilmiş seçim (Shift+Click, Ctrl+Click)
    """
    
    # Sinyaller
    row_double_clicked = pyqtSignal(int)  # row_id
    rows_selected = pyqtSignal(list)  # [row_id, ...] - yeni sinyal
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._main_window = parent  # Ana pencere referansı
        self._setup_performance()
        self._setup_selection()
        self._setup_headers()
        self._setup_context_menu()
    
    def setModel(self, model):
        """
        Model ayarlandığında selection sinyalini bağla.
        
        KRİTİK: setModel() çağrıldığında selectionModel değişir!
        Bu yüzden sinyal bağlantısı burada yapılmalı.
        """
        super().setModel(model)
        
        # Yeni selectionModel'e bağlan
        if self.selectionModel():
            self.selectionModel().selectionChanged.connect(self._on_internal_selection_changed)
            logger.debug("[TranslationTableView] Selection signal connected after setModel")
    
    def _on_internal_selection_changed(self, selected, deselected):
        """
        Selection değiştiğinde tetiklenir.
        Main window'un UI'ını günceller.
        """
        selection_model = self.selectionModel()
        if not selection_model:
            return
        
        selected_rows = selection_model.selectedRows()
        selected_count = len(selected_rows)
        
        logger.debug(f"[TranslationTableView] Selection changed: {selected_count} rows selected")
        
        # Sinyal emit et
        row_ids = self.get_selected_row_ids()
        self.rows_selected.emit(row_ids)
        
        # Main window'un UI state'ini güncelle
        if self._main_window and hasattr(self._main_window, '_update_ui_state'):
            self._main_window._update_ui_state()
        
        # Current item index'i güncelle
        if row_ids and self._main_window and hasattr(self._main_window, '_set_current_item_index'):
            self._main_window._set_current_item_index(row_ids[-1])
    
    def _setup_performance(self) -> None:
        """Performans için kritik ayarlar."""
        
        # Word wrap KAPALI - performans için kritik
        self.setWordWrap(False)
        
        # Tek tip satır yüksekliği - performans için kritik
        # QTableView için verticalHeader kullanılır (setUniformRowHeights QTreeView için)
        self.verticalHeader().setDefaultSectionSize(25)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        
        # Metin kırpma modu
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        
        # Alternatif satır renkleri (zaten model'de yapıyoruz ama burada da açabiliriz)
        self.setAlternatingRowColors(False)  # Model'den alıyoruz
        
        # Scroll modu - pixel bazlı daha smooth
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        
        # Grid çizgileri
        self.setShowGrid(True)
        self.setGridStyle(Qt.PenStyle.SolidLine)
    
    def _setup_selection(self) -> None:
        """Seçim ayarları."""
        
        # Satır bazlı seçim
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        # Genişletilmiş seçim (Ctrl+Click, Shift+Click)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        
        # Dikey başlık gizli
        self.verticalHeader().setVisible(False)
    
    def _setup_headers(self) -> None:
        """Başlık ayarları."""
        header = self.horizontalHeader()
        
        # Sıralama KAPALI - satırların karışmasını önler
        # NOT: dataChanged sinyali sıralama tetikleyebiliyor, bu yüzden kapalı
        self.setSortingEnabled(False)
        
        # Sort indicator gizli (sıralama kapalı olduğu için)
        header.setSortIndicatorShown(False)
        
        # Sütun boyutlandırma modları
        # NOT: ResizeToContents KULLANILMAZ - çok yavaş!
        # Stretch yerine Interactive kullanıyoruz
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        # Varsayılan sütun genişlikleri ayarlanacak (set_default_column_widths ile)
        header.setStretchLastSection(True)
    
    def set_default_column_widths(self) -> None:
        """
        Varsayılan sütun genişliklerini ayarla.
        
        ResizeToContents yerine sabit genişlikler kullanıyoruz.
        Bu, büyük tablolarda performans için kritiktir.
        """
        from gui.models.translation_table_model import TableColumn
        
        header = self.horizontalHeader()
        
        # Sabit genişlikler (piksel)
        widths = {
            TableColumn.LINE_NUM: 50,      # #
            TableColumn.TYPE: 70,          # Type
            TableColumn.TAG: 100,          # Tag
            TableColumn.ORIGINAL: 300,     # Original
            TableColumn.EDITABLE: 300,     # Editable (stretch)
            TableColumn.MODIFIED: 40,      # Mod.
            TableColumn.BREAKPOINT: 40,    # BP
            TableColumn.STATUS: 50,        # Status
        }
        
        for col, width in widths.items():
            if col < self.model().columnCount() if self.model() else 0:
                header.resizeSection(col, width)
    
    def _setup_context_menu(self) -> None:
        """Sağ tık menüsü."""
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
    
    def _show_context_menu(self, pos) -> None:
        """Context menu göster."""
        menu = QMenu(self)
        
        # Kopyala
        copy_action = QAction("Kopyala (Ctrl+C)", self)
        copy_action.triggered.connect(self.copy_selection_to_clipboard)
        menu.addAction(copy_action)
        
        # Tüm satırı kopyala
        copy_row_action = QAction("Tüm Satırı Kopyala", self)
        copy_row_action.triggered.connect(self.copy_full_rows_to_clipboard)
        menu.addAction(copy_row_action)
        
        menu.exec(self.viewport().mapToGlobal(pos))
    
    def keyPressEvent(self, event) -> None:
        """Klavye kısayolları."""
        if event.matches(QKeySequence.StandardKey.Copy):
            self.copy_selection_to_clipboard()
        else:
            super().keyPressEvent(event)
    
    def copy_selection_to_clipboard(self) -> None:
        """
        Seçili hücreleri panoya kopyala (TSV formatı).
        
        Satır bazlı seçim modunda tüm görünür sütunlar kopyalanır.
        """
        model = self.model()
        if not model:
            return
        
        selection = self.selectionModel()
        if not selection.hasSelection():
            return
        
        # Seçili satırları al
        indexes = selection.selectedIndexes()
        if not indexes:
            return
        
        # Satır ve sütun bazında grupla
        rows_data = {}
        for index in indexes:
            row = index.row()
            col = index.column()
            text = model.data(index, Qt.ItemDataRole.DisplayRole) or ""
            
            if row not in rows_data:
                rows_data[row] = {}
            rows_data[row][col] = str(text)
        
        # Sıralı satırlar
        sorted_rows = sorted(rows_data.keys())
        
        # Sütun sayısı
        col_count = model.columnCount()
        
        # TSV oluştur
        lines = []
        for row in sorted_rows:
            cols = rows_data[row]
            line_parts = []
            for col in range(col_count):
                line_parts.append(cols.get(col, ""))
            lines.append("\t".join(line_parts))
        
        tsv_text = "\n".join(lines)
        
        # Panoya kopyala
        clipboard = QApplication.clipboard()
        clipboard.setText(tsv_text)
        
        logger.debug(f"[TranslationTableView] Copied {len(sorted_rows)} rows to clipboard")
    
    def copy_full_rows_to_clipboard(self) -> None:
        """Seçili satırların tamamını kopyala."""
        self.copy_selection_to_clipboard()
    
    def get_selected_row_ids(self) -> List[int]:
        """
        Seçili satırların row_id'lerini döndür.
        
        NOT: Bu metod proxy model üzerinden çalışır.
        Source model'e erişmek için mapToSource kullanılır.
        """
        model = self.model()
        if not model:
            return []
        
        selection = self.selectionModel()
        if not selection.hasSelection():
            return []
        
        row_ids = []
        selected_rows = set()
        
        for index in selection.selectedIndexes():
            row = index.row()
            if row in selected_rows:
                continue
            selected_rows.add(row)
            
            # UserRole'dan row_id al
            row_id = model.data(model.index(row, 0), Qt.ItemDataRole.UserRole)
            if row_id is not None:
                row_ids.append(row_id)
        
        return row_ids
    
    def select_row_by_id(self, row_id: int) -> bool:
        """ID ile satır seç."""
        model = self.model()
        if not model:
            return False
        
        # Tüm satırlarda ara
        for row in range(model.rowCount()):
            idx = model.index(row, 0)
            if model.data(idx, Qt.ItemDataRole.UserRole) == row_id:
                self.selectRow(row)
                self.scrollTo(idx)
                return True
        
        return False
    
    def scroll_to_row_by_id(self, row_id: int) -> bool:
        """ID ile satıra scroll et."""
        model = self.model()
        if not model:
            return False
        
        for row in range(model.rowCount()):
            idx = model.index(row, 0)
            if model.data(idx, Qt.ItemDataRole.UserRole) == row_id:
                self.scrollTo(idx, QAbstractItemView.ScrollHint.PositionAtCenter)
                return True
        
        return False
