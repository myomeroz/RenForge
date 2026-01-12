# -*- coding: utf-8 -*-
"""
TranslationTableModel - Ana Veri Modeli

Bu model, QTableWidget yerine QTableView ile kullanılmak üzere tasarlanmıştır.
Virtual scrolling sayesinde sadece görünen satırlar render edilir.

PERFORMANS GARANTİLERİ:
- data() O(1): Sadece list[index] erişimi
- Hiç QTableWidgetItem oluşturulmaz
- QBrush/QColor cache'lenir
- Batch dataChanged sinyalleri
"""

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from PyQt6.QtCore import (
    Qt, QAbstractTableModel, QModelIndex, QPersistentModelIndex
)
from PyQt6.QtGui import QBrush, QColor

from renforge_logger import get_logger

logger = get_logger("gui.models.table")


# =============================================================================
# SÜTUN TANIMLARI
# =============================================================================

class TableColumn:
    """Tablo sütun indeksleri ve isimleri - eski tablo yapısıyla uyumlu."""
    LINE_NUM = 0      # Satır numarası
    TYPE = 1          # Tip (dialogue, string, var)
    TAG = 2           # Karakter etiketi
    ORIGINAL = 3      # Orijinal metin
    EDITABLE = 4      # Düzenlenebilir metin (Editable - eski yapı ile uyumlu)
    MODIFIED = 5      # Değiştirildi mi (*)
    BREAKPOINT = 6    # Marker (B)
    STATUS = 7        # Batch durumu (emoji)
    
    # Eski tablo başlıklarıyla aynı
    HEADERS = ['#', 'Type', 'Tag', 'Original', 'Editable', 'Mod.', 'BP', 'Status']
    COUNT = 8


# =============================================================================
# RENK CACHE - data() içinde obje oluşturmamak için
# =============================================================================

class ColorCache:
    """Sık kullanılan renkler için cache. Her çağrıda yeni obje oluşturulmaz."""
    
    # Arka plan renkleri
    BG_EVEN = QBrush(QColor("#2b2b2b"))
    BG_ODD = QBrush(QColor("#3c3f41"))
    BG_BREAKPOINT = QBrush(QColor("#5e5e3c"))
    BG_MODIFIED = QBrush(QColor("#1e3a1e"))
    
    # Metin renkleri
    FG_DEFAULT = QBrush(QColor("#f0f0f0"))
    FG_MODIFIED = QBrush(QColor("#ADD8E6"))
    FG_ERROR = QBrush(QColor("#ff6b6b"))
    FG_SUCCESS = QBrush(QColor("#90EE90"))
    
    # Status renkleri
    STATUS_OK = QBrush(QColor("#90EE90"))
    STATUS_FAIL = QBrush(QColor("#ff6b6b"))
    STATUS_WARN = QBrush(QColor("#FFD700"))


# =============================================================================
# SATIR VERİ YAPISI
# =============================================================================

@dataclass
class TableRowData:
    """
    Tek bir tablo satırının verisi.
    
    row_id: Benzersiz satır kimliği (proxy sıralaması değişse bile güncelleme
            için kullanılır). Genellikle item_index veya line_index olur.
    """
    row_id: int                    # Benzersiz ID (güncelleme için kritik!)
    line_num: str                  # Görüntülenecek satır numarası
    item_type: str                 # dialogue, string, var
    tag: str                       # Karakter etiketi
    original: str                  # Orijinal metin
    translation: str               # Çeviri
    is_modified: bool = False      # Değiştirildi mi
    has_breakpoint: bool = False   # Marker var mı
    batch_marker: str = ""         # OK, AI_FAIL, AI_WARN
    batch_tooltip: str = ""        # Hata detayı
    
    def get_status_display(self) -> str:
        """Status emoji döndür."""
        if self.batch_marker == "AI_FAIL":
            return "🔴"
        elif self.batch_marker == "AI_WARN":
            return "⚠️"
        elif self.batch_marker == "OK":
            return "✅"
        return ""


# =============================================================================
# ANA MODEL
# =============================================================================

class TranslationTableModel(QAbstractTableModel):
    """
    Çeviri tablosu için ana veri modeli.
    
    NEDEN DONMA OLMAZ:
    1. Virtual scrolling: QTableView sadece görünen satırları ister
    2. data() O(1): Sadece list[row] erişimi  
    3. Hiç widget oluşturulmaz
    4. Batch dataChanged: Tüm güncellemeler tek sinyalde
    
    KULLANIM:
        model = TranslationTableModel()
        model.set_rows(all_rows)  # İlk yükleme
        model.update_rows_by_id({row_id: {"translation": "..."}})  # Güncelleme
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Ana veri deposu (list erişimi O(1))
        self._rows: List[TableRowData] = []
        
        # row_id -> list index mapping (güncelleme için O(1) lookup)
        self._id_to_index: Dict[int, int] = {}
    
    # =========================================================================
    # QAbstractTableModel ZORUNLU METODLARİ
    # =========================================================================
    
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Satır sayısı."""
        if parent.isValid():
            return 0
        return len(self._rows)
    
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Sütun sayısı."""
        if parent.isValid():
            return 0
        return TableColumn.COUNT
    
    def headerData(self, section: int, orientation: Qt.Orientation, 
                   role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Başlık verisi."""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(TableColumn.HEADERS):
                return TableColumn.HEADERS[section]
        return None
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """
        Hücre verisi döndür.
        
        KRİTİK PERFORMANS: Bu metod saniyede binlerce kez çağrılabilir.
        Sadece O(1) işlemler yapılmalı. Obje oluşturmaktan kaçınılmalı.
        """
        if not index.isValid():
            return None
        
        row_idx = index.row()
        col_idx = index.column()
        
        if row_idx < 0 or row_idx >= len(self._rows):
            return None
        
        row = self._rows[row_idx]
        
        # DisplayRole - Metin gösterimi
        if role == Qt.ItemDataRole.DisplayRole:
            return self._get_display_value(row, col_idx)
        
        # ForegroundRole - Metin rengi
        elif role == Qt.ItemDataRole.ForegroundRole:
            if row.is_modified:
                return ColorCache.FG_MODIFIED
            if row.batch_marker == "AI_FAIL":
                return ColorCache.FG_ERROR
            return ColorCache.FG_DEFAULT
        
        # BackgroundRole - Arka plan rengi
        elif role == Qt.ItemDataRole.BackgroundRole:
            if row.has_breakpoint:
                return ColorCache.BG_BREAKPOINT
            return ColorCache.BG_EVEN if row_idx % 2 == 0 else ColorCache.BG_ODD
        
        # ToolTipRole - Tooltip
        elif role == Qt.ItemDataRole.ToolTipRole:
            if col_idx == TableColumn.STATUS and row.batch_tooltip:
                return row.batch_tooltip
            return None
        
        # UserRole - Satır ID'si (seçim/güncelleme için)
        elif role == Qt.ItemDataRole.UserRole:
            return row.row_id
        
        # TextAlignmentRole - Hizalama
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col_idx in (TableColumn.MODIFIED, TableColumn.BREAKPOINT, TableColumn.STATUS):
                return Qt.AlignmentFlag.AlignCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        
        return None
    
    def _get_display_value(self, row: TableRowData, col: int) -> str:
        """Sütuna göre görüntülenecek değer."""
        if col == TableColumn.LINE_NUM:
            return row.line_num
        elif col == TableColumn.TYPE:
            return row.item_type
        elif col == TableColumn.TAG:
            return row.tag
        elif col == TableColumn.ORIGINAL:
            return row.original
        elif col == TableColumn.EDITABLE:
            return row.translation
        elif col == TableColumn.MODIFIED:
            return "*" if row.is_modified else ""
        elif col == TableColumn.BREAKPOINT:
            return "B" if row.has_breakpoint else ""
        elif col == TableColumn.STATUS:
            return row.get_status_display()
        return ""
    
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Hücre bayrakları."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        
        base_flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        
        # Sadece Editable sütunu düzenlenebilir
        if index.column() == TableColumn.EDITABLE:
            return base_flags | Qt.ItemFlag.ItemIsEditable
        
        return base_flags
    
    def setData(self, index: QModelIndex, value: Any, 
                role: int = Qt.ItemDataRole.EditRole) -> bool:
        """Hücre verisi güncelle (düzenleme için)."""
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False
        
        if index.column() != TableColumn.EDITABLE:
            return False
        
        row_idx = index.row()
        if row_idx < 0 or row_idx >= len(self._rows):
            return False
        
        new_text = str(value) if value else ""
        old_text = self._rows[row_idx].translation
        
        if new_text != old_text:
            self._rows[row_idx].translation = new_text
            self._rows[row_idx].is_modified = True
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])
            return True
        
        return False
    
    # =========================================================================
    # VERİ YÖNETİM API'Sİ
    # =========================================================================
    
    def set_rows(self, rows: List[TableRowData]) -> None:
        """
        Tüm satırları değiştir (ilk yükleme veya reset).
        
        Bu işlem O(n) ama sadece bir kez yapılır ve 
        beginResetModel/endResetModel ile sarılır.
        """
        self.beginResetModel()
        
        self._rows = rows
        self._rebuild_id_index()
        
        self.endResetModel()
        
        logger.debug(f"[TranslationTableModel] Loaded {len(rows)} rows")
    
    def append_rows(self, new_rows: List[TableRowData]) -> None:
        """Yeni satırlar ekle (chunk bazlı yükleme için)."""
        if not new_rows:
            return
        
        start_row = len(self._rows)
        end_row = start_row + len(new_rows) - 1
        
        self.beginInsertRows(QModelIndex(), start_row, end_row)
        
        for row in new_rows:
            self._rows.append(row)
            self._id_to_index[row.row_id] = len(self._rows) - 1
        
        self.endInsertRows()
    
    def update_rows_by_id(self, updates: Dict[int, Dict[str, Any]]) -> None:
        """
        ID bazlı toplu güncelleme.
        
        Bu metod, proxy sıralaması değişse bile doğru satırları günceller.
        Batch dataChanged sinyali ile performanslı güncelleme yapar.
        
        Args:
            updates: {row_id: {"translation": "...", "is_modified": True, ...}}
        """
        if not updates:
            return
        
        # Etkilenen satır indekslerini topla
        affected_indices = []
        
        for row_id, patch in updates.items():
            idx = self._id_to_index.get(row_id)
            if idx is None:
                continue
            
            row = self._rows[idx]
            changed = False
            
            # Patch uygula
            for key, value in patch.items():
                if hasattr(row, key):
                    old_val = getattr(row, key)
                    if old_val != value:
                        setattr(row, key, value)
                        changed = True
            
            if changed:
                affected_indices.append(idx)
        
        # Batch dataChanged - sadece bir sinyal
        if affected_indices:
            affected_indices.sort()
            min_row = affected_indices[0]
            max_row = affected_indices[-1]
            
            top_left = self.index(min_row, 0)
            bottom_right = self.index(max_row, TableColumn.COUNT - 1)
            
            self.dataChanged.emit(top_left, bottom_right)
            
            logger.info(f"[TranslationTableModel] Updated {len(affected_indices)} rows by ID, dataChanged emitted for rows {min_row}-{max_row}")
        else:
            logger.info(f"[TranslationTableModel] update_rows_by_id called with {len(updates)} updates but NO rows were affected!")
    
    def update_single_row(self, row_id: int, patch: Dict[str, Any]) -> None:
        """Tek satır güncelle (eski API uyumluluğu için)."""
        self.update_rows_by_id({row_id: patch})
    
    def get_row_by_id(self, row_id: int) -> Optional[TableRowData]:
        """ID ile satır getir."""
        idx = self._id_to_index.get(row_id)
        if idx is not None and 0 <= idx < len(self._rows):
            return self._rows[idx]
        return None
    
    def get_row_by_index(self, index: int) -> Optional[TableRowData]:
        """İndeks ile satır getir."""
        if 0 <= index < len(self._rows):
            return self._rows[index]
        return None
    
    def get_all_rows(self) -> List[TableRowData]:
        """Tüm satırları döndür."""
        return self._rows
    
    def clear(self) -> None:
        """Tüm veriyi temizle."""
        self.beginResetModel()
        self._rows = []
        self._id_to_index = {}
        self.endResetModel()
    
    def _rebuild_id_index(self) -> None:
        """ID -> index mapping'i yeniden oluştur."""
        self._id_to_index = {row.row_id: idx for idx, row in enumerate(self._rows)}
