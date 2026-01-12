# -*- coding: utf-8 -*-
"""
TranslationFilterProxyModel - Filtreleme ve Sıralama

Bu proxy model, ana modelin üzerine filtreleme ve sıralama ekler.
Orijinal veri değişmez, sadece görünüm filtrelenir.
"""

from typing import Optional

from PyQt6.QtCore import (
    Qt, QSortFilterProxyModel, QModelIndex
)

from renforge_logger import get_logger

logger = get_logger("gui.models.filter_proxy")


class TranslationFilterProxyModel(QSortFilterProxyModel):
    """
    Çeviri tablosu için filtreleme ve sıralama proxy'si.
    
    ÖZELLİKLER:
    - Case-insensitive arama
    - Sütun bazlı filtreleme
    - Status filtresi (Pending/Done/Failed)
    - Doğal sıralama
    
    ROW ID UYARISI:
    Proxy sıralaması satır indekslerini değiştirir!
    Güncelleme yaparken MUTLAKA row_id kullanın, index DEĞİL.
    """
    
    # Filter tipleri
    FILTER_ALL = "all"
    FILTER_MODIFIED = "changed"
    FILTER_FAILED = "ai_fail"
    FILTER_WARNING = "ai_warn"
    FILTER_EMPTY = "empty"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Filtreleme ayarları
        self._search_text: str = ""
        self._search_column: int = -1  # -1 = tüm sütunlar
        self._status_filter: str = self.FILTER_ALL
        
        # Case-insensitive arama
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        
        # Dinamik sıralama KAPALI - veri değiştiğinde yeniden sıralama YAPILMAZ
        # Bu, dataChanged sinyali geldiğinde satırların karışmasını önler
        self.setDynamicSortFilter(False)
        
        # Recursive filtreleme (tree için, burada kullanılmıyor)
        self.setRecursiveFilteringEnabled(False)
    
    def set_search_text(self, text: str, column: int = -1) -> None:
        """
        Arama metni ayarla.
        
        Args:
            text: Aranacak metin
            column: Aranacak sütun (-1 = tüm sütunlar)
        """
        self._search_text = text.lower()
        self._search_column = column
        self.invalidateFilter()
    
    def set_status_filter(self, status: str) -> None:
        """
        Status filtresi ayarla.
        
        Args:
            status: FILTER_ALL, FILTER_MODIFIED, FILTER_FAILED, FILTER_WARNING, FILTER_EMPTY
        """
        self._status_filter = status
        self.invalidateFilter()
    
    def clear_filters(self) -> None:
        """Tüm filtreleri temizle."""
        self._search_text = ""
        self._search_column = -1
        self._status_filter = self.FILTER_ALL
        self.invalidateFilter()
    
    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """
        Satırın filtreyi geçip geçmediğini kontrol et.
        
        PERFORMANS: Bu metod her satır için çağrılır.
        Ağır işlemlerden kaçının.
        """
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
    
    def _check_status_filter(self, model, row: int) -> bool:
        """Status filtresi kontrolü."""
        from gui.models.translation_table_model import TableColumn
        
        if self._status_filter == self.FILTER_MODIFIED:
            # Modified sütunu "*" içeriyor mu?
            idx = model.index(row, TableColumn.MODIFIED)
            return model.data(idx, Qt.ItemDataRole.DisplayRole) == "*"
        
        elif self._status_filter == self.FILTER_FAILED:
            # Status sütunu fail emoji içeriyor mu?
            idx = model.index(row, TableColumn.STATUS)
            return model.data(idx, Qt.ItemDataRole.DisplayRole) == "🔴"
        
        elif self._status_filter == self.FILTER_WARNING:
            idx = model.index(row, TableColumn.STATUS)
            return model.data(idx, Qt.ItemDataRole.DisplayRole) == "⚠️"
        
        elif self._status_filter == self.FILTER_EMPTY:
            # Editable sütunu boş mu?
            idx = model.index(row, TableColumn.EDITABLE)
            text = model.data(idx, Qt.ItemDataRole.DisplayRole) or ""
            return not text.strip()
        
        return True
    
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
    
    def get_source_row_id(self, proxy_row: int) -> Optional[int]:
        """
        Proxy satır indeksinden kaynak row_id'yi al.
        
        Güncelleme yaparken bu metod kullanılmalı!
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
        return [self.get_source_row_id(row) for row in proxy_rows if self.get_source_row_id(row) is not None]
