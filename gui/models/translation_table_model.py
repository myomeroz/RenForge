# -*- coding: utf-8 -*-
"""
TranslationTableModel - Ana Veri Modeli (v2)

Bu model, QTableWidget yerine QTableView ile kullanılmak üzere tasarlanmıştır.
Virtual scrolling sayesinde sadece görünen satırlar render edilir.

v2 Değişiklikleri:
- Incremental counters (_stats, _flagged_count) eklendi
- stats_updated sinyali eklendi
- update_row_by_id() ID bazlı güncelleme
- get_index_by_id() helper
- O(1) counter güncellemesi için _update_stats_delta()

PERFORMANS GARANTİLERİ:
- data() O(1): Sadece list[index] erişimi
- Hiç QTableWidgetItem oluşturulmaz
- QBrush/QColor cache'lenir
- Counters O(1) güncelleme (tam scan yok)
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from PySide6.QtCore import (
    Qt, QAbstractTableModel, QModelIndex, Signal
)
from PySide6.QtGui import QBrush, QColor

from renforge_logger import get_logger
from gui.models.row_data import RowData, RowStatus

logger = get_logger("gui.models.table")


# =============================================================================
# SÜTUN TANIMLARI
# =============================================================================

class TableColumn:
    """Tablo sütun indeksleri ve isimleri."""
    LINE_NUM = 0      # Satır numarası
    TYPE = 1          # Tip (dialogue, string, var)
    TAG = 2           # Karakter etiketi
    ORIGINAL = 3      # Orijinal metin
    EDITABLE = 4      # Düzenlenebilir metin
    MODIFIED = 5      # Değiştirildi mi (*)
    BREAKPOINT = 6    # Marker (🚩)
    STATUS = 7        # Status icon
    
    HEADERS = ['#', 'Type', 'Tag', 'Original', 'Editable', 'Mod.', 'BP', 'Status']
    COUNT = 8


# =============================================================================
# RENK CACHE
# =============================================================================

class ColorCache:
    """Sık kullanılan renkler için cache."""
    
    # Arka plan renkleri
    BG_EVEN = QBrush(QColor("#2b2b2b"))
    BG_ODD = QBrush(QColor("#3c3f41"))
    BG_BREAKPOINT = QBrush(QColor("#5e5e3c"))
    BG_MODIFIED = QBrush(QColor("#1e3a1e"))
    BG_APPROVED = QBrush(QColor("#1e3a1e"))
    BG_ERROR = QBrush(QColor("#3a1e1e"))
    
    # Metin renkleri
    FG_DEFAULT = QBrush(QColor("#f0f0f0"))
    FG_MODIFIED = QBrush(QColor("#ADD8E6"))  # Light Blue
    FG_TRANSLATED = QBrush(QColor("#90EE90"))  # Light Green
    FG_APPROVED = QBrush(QColor("#00FF00"))   # Green
    FG_ERROR = QBrush(QColor("#ff6b6b"))      # Red
    FG_FLAGGED = QBrush(QColor("#FFA500"))    # Orange


# =============================================================================
# ANA MODEL
# =============================================================================

class TranslationTableModel(QAbstractTableModel):
    """
    Çeviri tablosu için ana veri modeli (v2).
    
    RowData ve RowStatus yapılarını kullanır.
    Incremental counter'lar ile O(1) stats güncellemesi sağlar.
    """
    
    # === Sinyaller ===
    row_updated = Signal(int, object)  # (index, RowData)
    stats_updated = Signal(dict)       # {status: count, flagged: count, total: count}
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Ana veri deposu (list erişimi O(1))
        self._rows: List[RowData] = []
        
        # row_id -> list index mapping (O(1) lookup)
        self._id_to_index: Dict[str, int] = {}
        
        # === INCREMENTAL COUNTERS (v2) ===
        self._stats: Dict[RowStatus, int] = {status: 0 for status in RowStatus}
        self._flagged_count: int = 0
    
    # =========================================================================
    # QAbstractTableModel ZORUNLU METODLARİ
    # =========================================================================
    
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)
    
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return TableColumn.COUNT
    
    def headerData(self, section: int, orientation: Qt.Orientation, 
                   role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(TableColumn.HEADERS):
                return TableColumn.HEADERS[section]
        return None
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        
        row_idx = index.row()
        col_idx = index.column()
        
        if row_idx < 0 or row_idx >= len(self._rows):
            return None
        
        row = self._rows[row_idx]
        
        # DisplayRole
        if role == Qt.ItemDataRole.DisplayRole:
            return self._get_display_value(row, col_idx, row_idx)
        
        # ForegroundRole
        elif role == Qt.ItemDataRole.ForegroundRole:
            if row.status == RowStatus.ERROR:
                return ColorCache.FG_ERROR
            if row.is_flagged:
                return ColorCache.FG_FLAGGED
            if row.status == RowStatus.APPROVED:
                return ColorCache.FG_APPROVED
            if row.status == RowStatus.MODIFIED:
                return ColorCache.FG_MODIFIED
            if row.status == RowStatus.TRANSLATED:
                return ColorCache.FG_TRANSLATED
            return ColorCache.FG_DEFAULT
        
        # BackgroundRole
        elif role == Qt.ItemDataRole.BackgroundRole:
            if row.status == RowStatus.ERROR:
                return ColorCache.BG_ERROR
            return ColorCache.BG_EVEN if row_idx % 2 == 0 else ColorCache.BG_ODD
        
        # ToolTipRole
        elif role == Qt.ItemDataRole.ToolTipRole:
            if col_idx == TableColumn.STATUS:
                return f"Status: {row.status.value}\nFlagged: {row.is_flagged}\nError: {row.error_message or 'None'}"
            if col_idx == TableColumn.EDITABLE and row.notes:
                return f"Note: {row.notes}"
            return None
        
        # UserRole - row_id
        elif role == Qt.ItemDataRole.UserRole:
            return row.id
        
        # TextAlignmentRole
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col_idx in (TableColumn.MODIFIED, TableColumn.BREAKPOINT, TableColumn.STATUS):
                return Qt.AlignmentFlag.AlignCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        
        return None
    
    def _get_display_value(self, row: RowData, col: int, row_idx: int) -> str:
        if col == TableColumn.LINE_NUM:
            return str(row_idx + 1)
        elif col == TableColumn.TYPE:
            return str(row.row_type)
        elif col == TableColumn.TAG:
            return str(row.tag or "")
        elif col == TableColumn.ORIGINAL:
            return str(row.original_text)
        elif col == TableColumn.EDITABLE:
            return str(row.editable_text or "")
        elif col == TableColumn.MODIFIED:
            return "*" if row.is_dirty else ""
        elif col == TableColumn.BREAKPOINT:
            return "🚩" if row.is_flagged else ""
        elif col == TableColumn.STATUS:
            return self._get_status_icon(row)
        return ""
    
    def _get_status_icon(self, row: RowData) -> str:
        if row.status == RowStatus.APPROVED:
            return "✔"
        elif row.status == RowStatus.ERROR:
            return "⚠"
        elif row.status == RowStatus.TRANSLATED:
            return "✓"
        elif row.status == RowStatus.MODIFIED:
            return "★"
        elif row.status == RowStatus.UNTRANSLATED:
            return "○"
        return ""

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        
        base_flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        
        if index.column() == TableColumn.EDITABLE:
            return base_flags | Qt.ItemFlag.ItemIsEditable
        
        return base_flags
    
    def setData(self, index: QModelIndex, value: Any, 
                role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False
        
        if index.column() != TableColumn.EDITABLE:
            return False
        
        row_idx = index.row()
        if row_idx < 0 or row_idx >= len(self._rows):
            return False
        
        new_text = str(value) if value is not None else ""
        row = self._rows[row_idx]
        
        # Capture old state for delta update
        old_status = row.status
        old_flagged = row.is_flagged
        
        # Use RowData's update_text (handles APPROVED→MODIFIED)
        row.update_text(new_text)
        
        # Update incremental counters
        self._update_stats_delta(old_status, row.status, old_flagged, row.is_flagged)
        
        # Emit dataChanged for entire row
        top_left = self.index(row_idx, 0)
        bottom_right = self.index(row_idx, TableColumn.COUNT - 1)
        self.dataChanged.emit(top_left, bottom_right)
        
        self.row_updated.emit(row_idx, row)
        
        return True
    
    # =========================================================================
    # INCREMENTAL COUNTERS (v2)
    # =========================================================================
    
    def _recompute_all_stats(self) -> None:
        """Full recount. Only on initial load."""
        self._stats = {status: 0 for status in RowStatus}
        self._flagged_count = 0
        for row in self._rows:
            self._stats[row.status] += 1
            if row.is_flagged:
                self._flagged_count += 1
        self.stats_updated.emit(self.get_global_stats())
    
    def _update_stats_delta(self, old_status: RowStatus, new_status: RowStatus,
                            old_flagged: bool, new_flagged: bool) -> None:
        """O(1) incremental counter update."""
        changed = False
        if old_status != new_status:
            self._stats[old_status] -= 1
            self._stats[new_status] += 1
            changed = True
        if old_flagged != new_flagged:
            self._flagged_count += (1 if new_flagged else -1)
            changed = True
        if changed:
            self.stats_updated.emit(self.get_global_stats())
    
    def get_global_stats(self) -> dict:
        """Return current counters. O(1)."""
        return {
            "total": len(self._rows),
            "untranslated": self._stats[RowStatus.UNTRANSLATED],
            "translated": self._stats[RowStatus.TRANSLATED],
            "modified": self._stats[RowStatus.MODIFIED],
            "approved": self._stats[RowStatus.APPROVED],
            "error": self._stats[RowStatus.ERROR],
            "flagged": self._flagged_count,
        }
    
    # =========================================================================
    # VERİ YÖNETİM API'Sİ
    # =========================================================================
    
    def set_rows(self, rows: List[RowData]) -> None:
        """Tüm satırları değiştir. O(N) sadece load'da."""
        self.beginResetModel()
        self._rows = rows
        self._rebuild_id_index()
        self.endResetModel()
        
        # Recompute counters once
        self._recompute_all_stats()
        
        logger.debug(f"[TranslationTableModel] Loaded {len(rows)} rows")
    
    def append_rows(self, new_rows: List[RowData]) -> None:
        """Yeni satırlar ekle."""
        if not new_rows:
            return
        
        start_row = len(self._rows)
        end_row = start_row + len(new_rows) - 1
        
        self.beginInsertRows(QModelIndex(), start_row, end_row)
        
        for row in new_rows:
            self._rows.append(row)
            self._id_to_index[str(row.id)] = len(self._rows) - 1
            # Update counters
            self._stats[row.status] += 1
            if row.is_flagged:
                self._flagged_count += 1
        
        self.endInsertRows()
        self.stats_updated.emit(self.get_global_stats())
    
    def get_row_data(self, row_idx: int) -> Optional[RowData]:
        """Satır verisini döndür."""
        if 0 <= row_idx < len(self._rows):
            return self._rows[row_idx]
        return None
    
    def get_all_rows(self) -> List[RowData]:
        """Tüm satırları döndür. Export/batch için, UI redraw için KULLANMA."""
        return self._rows
    
    def get_index_by_id(self, row_id: str) -> Optional[int]:
        """ID'den index bul. O(1)."""
        return self._id_to_index.get(str(row_id))
    
    def get_row_by_id(self, row_id: str) -> Optional[RowData]:
        """
        ID'den satır verisini döndür. O(1).
        
        Args:
            row_id: Satır ID'si (string)
            
        Returns:
            RowData object veya None (bulunamadıysa)
        """
        idx = self.get_index_by_id(row_id)
        if idx is not None:
            return self.get_row_data(idx)
        return None
    
    # =========================================================================
    # ID-BASED UPDATE API (v2)
    # =========================================================================
    
    def update_row_by_id(self, row_id: str, patch: Dict[str, Any]) -> bool:
        """
        Tek satır güncelleme (ID bazlı).
        Incremental counter güncellemesi yapar.
        """
        idx = self._id_to_index.get(str(row_id))
        if idx is None:
            logger.warning(f"[model] Row ID not found: {row_id}")
            return False
        
        row = self._rows[idx]
        old_status = row.status
        old_flagged = row.is_flagged
        changed = False
        
        for key, value in patch.items():
            if hasattr(row, key):
                old_val = getattr(row, key)
                if old_val != value:
                    setattr(row, key, value)
                    changed = True
        
        if changed:
            # Update counters
            self._update_stats_delta(old_status, row.status, old_flagged, row.is_flagged)
            
            # Emit dataChanged
            top_left = self.index(idx, 0)
            bottom_right = self.index(idx, TableColumn.COUNT - 1)
            self.dataChanged.emit(top_left, bottom_right)
            
            self.row_updated.emit(idx, row)
        
        return changed
    
    def update_single_row(self, row_idx: int, patch: Dict[str, Any]) -> None:
        """
        Tek satır güncelleme (Index bazlı - Legacy Compatibility).
        """
        if not (0 <= row_idx < len(self._rows)):
            return
        
        row = self._rows[row_idx]
        old_status = row.status
        old_flagged = row.is_flagged
        changed = False
        
        for key, value in patch.items():
            if hasattr(row, key):
                old_val = getattr(row, key)
                if old_val != value:
                    setattr(row, key, value)
                    changed = True
        
        if changed:
            self._update_stats_delta(old_status, row.status, old_flagged, row.is_flagged)
            
            top_left = self.index(row_idx, 0)
            bottom_right = self.index(row_idx, TableColumn.COUNT - 1)
            self.dataChanged.emit(top_left, bottom_right)
            self.row_updated.emit(row_idx, row)

    def update_rows_by_id(self, updates: Dict[str, Dict[str, Any]]) -> None:
        """
        ID bazlı toplu güncelleme.
        """
        if not updates:
            return
        
        affected_indices = []
        
        for row_id, patch in updates.items():
            idx = self._id_to_index.get(str(row_id))
            if idx is None:
                continue
            
            row = self._rows[idx]
            old_status = row.status
            old_flagged = row.is_flagged
            changed = False
            
            for key, value in patch.items():
                if hasattr(row, key):
                    old_val = getattr(row, key)
                    if old_val != value:
                        setattr(row, key, value)
                        changed = True
            
            if changed:
                self._update_stats_delta(old_status, row.status, old_flagged, row.is_flagged)
                affected_indices.append(idx)
        
        if affected_indices:
            affected_indices.sort()
            min_row = affected_indices[0]
            max_row = affected_indices[-1]
            
            top_left = self.index(min_row, 0)
            bottom_right = self.index(max_row, TableColumn.COUNT - 1)
            self.dataChanged.emit(top_left, bottom_right)
    
    # =========================================================================
    # SAVE SNAPSHOT
    # =========================================================================
    
    def snapshot_all_for_save(self) -> None:
        """Called when file is saved. Updates last_saved_text for all rows."""
        for row in self._rows:
            row.snapshot_for_save()
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def _rebuild_id_index(self) -> None:
        """ID -> index mapping'i yeniden oluştur."""
        self._id_to_index = {str(row.id): idx for idx, row in enumerate(self._rows)}
