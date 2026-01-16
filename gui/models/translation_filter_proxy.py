# -*- coding: utf-8 -*-
"""
TranslationFilterProxyModel - Filtreleme ve Sıralama

Bu proxy model, ana modelin üzerine filtreleme ve sıralama ekler.
RowStatus modelini kullanarak esnek filtreleme sağlar.
"""

from typing import Optional

from PySide6.QtCore import (
    Qt, QSortFilterProxyModel, QModelIndex
)

from renforge_logger import get_logger
from gui.models.row_data import RowStatus

logger = get_logger("gui.models.filter_proxy")


class TranslationFilterProxyModel(QSortFilterProxyModel):
    """
    Çeviri tablosu için filtreleme ve sıralama proxy'si.
    
    ÖZELLİKLER:
    - Case-insensitive arama
    - Sütun bazlı filtreleme
    - Status filtresi (RowStatus enum tabanlı)
    - Doğal sıralama
    """
    
    # Filter tipleri
    FILTER_ALL = "all"
    FILTER_UNTRANSLATED = "untranslated"
    FILTER_TRANSLATED = "translated"
    FILTER_MODIFIED = "modified"
    FILTER_APPROVED = "approved"
    FILTER_ERROR = "error"
    FILTER_FLAGGED = "flagged"
    FILTER_PROBLEMS = "problems" # Untranslated + Error + Flagged
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Filtreleme ayarları
        self._search_text: str = ""
        self._search_column: int = -1  # -1 = tüm sütunlar
        self._status_filter: str = self.FILTER_ALL
        
        # Case-insensitive arama
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        
        # Dinamik sıralama KAPALI
        self.setDynamicSortFilter(False)
        self.setRecursiveFilteringEnabled(False)
    
    def set_search_text(self, text: str, column: int = -1) -> None:
        """Arama metni ayarla."""
        self._search_text = text.lower()
        self._search_column = column
        self.invalidateFilter()
    
    def set_status_filter(self, status: str) -> None:
        """Status filtresi ayarla."""
        self._status_filter = status
        self.invalidateFilter()
    
    def clear_filters(self) -> None:
        """Tüm filtreleri temizle."""
        self._search_text = ""
        self._search_column = -1
        self._status_filter = self.FILTER_ALL
        self.invalidateFilter()
    
    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """Satırın filtreyi geçip geçmediğini kontrol et."""
        model = self.sourceModel()
        if not model:
            return True
        
        # Status filtresi
        if self._status_filter != self.FILTER_ALL:
            if not self._check_status_filter(model, source_row):
                return False
        
        # Metin araması
        if self._search_text:
            if not self._check_search_filter(model, source_row):
                return False
        
        return True
    
    def _check_status_filter(self, model, row_idx: int) -> bool:
        """Status filtresi kontrolü - Modelden RowData alarak."""
        
        # Eğer model get_row_data metoduna sahipse direkt kullan
        # (TranslationTableModel bu metoda sahip)
        if hasattr(model, 'get_row_data'):
            row_data = model.get_row_data(row_idx)
            if not row_data:
                return False
                
            status = row_data.status
            is_flagged = row_data.is_flagged
            
            if self._status_filter == self.FILTER_UNTRANSLATED:
                return status == RowStatus.UNTRANSLATED
                
            elif self._status_filter == self.FILTER_TRANSLATED:
                return status == RowStatus.TRANSLATED
                
            elif self._status_filter == self.FILTER_MODIFIED:
                return status == RowStatus.MODIFIED
                
            elif self._status_filter == self.FILTER_APPROVED:
                return status == RowStatus.APPROVED
                
            elif self._status_filter == self.FILTER_ERROR:
                return status == RowStatus.ERROR
                
            elif self._status_filter == self.FILTER_FLAGGED:
                return is_flagged
                
            elif self._status_filter == self.FILTER_PROBLEMS:
                # Untranslated OR Error OR Flagged
                return (status in (RowStatus.UNTRANSLATED, RowStatus.ERROR)) or is_flagged
            
            return True
        
        return True # Fallback
    
    def _check_search_filter(self, model, row: int) -> bool:
        """Metin araması kontrolü."""
        if self._search_column >= 0:
            # Tek sütunda ara
            idx = model.index(row, self._search_column)
            text = model.data(idx, Qt.ItemDataRole.DisplayRole) or ""
            return self._search_text in text.lower()
        
        else:
            # Tüm sütunlarda ara
            for col in range(model.columnCount()):
                idx = model.index(row, col)
                text = model.data(idx, Qt.ItemDataRole.DisplayRole) or ""
                if self._search_text in text.lower():
                    return True
            return False
    
    def get_source_row_id(self, proxy_row: int) -> Optional[str]:
        """
        Proxy satır indeksinden kaynak row_id'yi al (str).
        """
        proxy_index = self.index(proxy_row, 0)
        source_index = self.mapToSource(proxy_index)
        
        if source_index.isValid():
            model = self.sourceModel()
            if model:
                return model.data(source_index, Qt.ItemDataRole.UserRole)
        
        return None
    
    def get_source_row_ids(self, proxy_rows: list) -> list:
        """Birden fazla proxy satırı için kaynak row_id'leri al."""
        ids = []
        for row in proxy_rows:
            rid = self.get_source_row_id(row)
            if rid is not None:
                ids.append(rid)
        return ids
